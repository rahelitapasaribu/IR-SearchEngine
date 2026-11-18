from __future__ import annotations

import html
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

# Pastikan semua path relatif mengacu pada folder project.
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from retrieval import InformationRetrieval  # noqa: E402

try:
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    STEMMER = StemmerFactory().create_stemmer()
except Exception:
    STEMMER = None

EVAL_FILE = BASE_DIR / "evaluation_judgments.json"

st.set_page_config(
    page_title="JUPITA Search Engine",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-title {font-size: 2rem; font-weight: 750; margin-bottom: .15rem;}
    .sub-title {color: #64748b; margin-bottom: 1.2rem;}
    .result-meta {color: #64748b; font-size: .88rem; margin-top: .3rem; margin-bottom: .6rem;}
    .score-badge {
        background-color: #f1f5f9; 
        color: #0f172a; 
        padding: 0.2rem 0.6rem; 
        border-radius: 6px; 
        font-weight: 600; 
        font-size: 0.85rem;
        border: 1px solid #e2e8f0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Memuat index dan model pencarian...")
def load_resources():
    """Memuat komponen retrieval, model TF-IDF, metadata, dan teks artikel."""
    import pickle

    required = [
        BASE_DIR / "index" / "dictionary.json",
        BASE_DIR / "index" / "kgram_index.json",
        BASE_DIR / "index" / "postings_vbe.bin",
        BASE_DIR / "index" / "vbe_index.json",
        BASE_DIR / "index" / "tfidf_model.pkl",
        BASE_DIR / "dataset" / "metadata_articles.csv",
        BASE_DIR / "processed" / "preprocessed_articles.csv",
    ]
    missing = [str(path.relative_to(BASE_DIR)) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "File pendukung berikut belum tersedia: " + ", ".join(missing)
        )

    retrieval = InformationRetrieval()

    with open(BASE_DIR / "index" / "tfidf_model.pkl", "rb") as file:
        model_data = pickle.load(file)

    model = model_data["model"]
    document_vectors = model_data["document_vectors"]

    metadata = pd.read_csv(BASE_DIR / "dataset" / "metadata_articles.csv")
    documents = pd.read_csv(BASE_DIR / "processed" / "preprocessed_articles.csv")

    metadata["id"] = metadata["id"].astype(str)
    documents["id"] = documents["id"].astype(str)

    text_columns = ["id", "text", "processed_text"]
    available_text_columns = [col for col in text_columns if col in documents.columns]
    corpus = metadata.merge(
        documents[available_text_columns],
        on="id",
        how="left",
    )

    corpus["text"] = corpus.get("text", pd.Series("", index=corpus.index)).fillna("")
    corpus["processed_text"] = corpus.get(
        "processed_text", pd.Series("", index=corpus.index)
    ).fillna("")

    return retrieval, model, document_vectors, corpus


def normalize_query(query: str) -> list[str]:
    """Membersihkan dan melakukan stemming query agar konsisten dengan korpus."""
    raw_tokens = re.findall(r"[a-zA-Z0-9_*?]+", query.lower())
    normalized = []

    for token in raw_tokens:
        if "*" in token or "?" in token:
            if (
                STEMMER is not None
                and token.endswith("*")
                and token.count("*") == 1
                and "?" not in token
            ):
                prefix = token[:-1]
                stemmed_prefix = STEMMER.stem(prefix)
                normalized.append((stemmed_prefix or prefix) + "*")
            else:
                normalized.append(token)
        elif STEMMER is not None:
            stemmed = STEMMER.stem(token)
            if stemmed:
                normalized.append(stemmed)
        else:
            normalized.append(token)

    return normalized


def extract_abstract(text: str) -> str:
    """Mengambil bagian abstrak Indonesia dari teks PDF hasil ekstraksi."""
    if not isinstance(text, str) or not text.strip():
        return "Abstrak belum tersedia pada data."

    clean_text = re.sub(r"[ \t]+", " ", text)
    patterns = [
        r"ABSTRAK\s*(.*?)(?=\n\s*(?:Kata\s+kunci|Kata\s+Kunci|ABSTRACT)\b)",
        r"ABSTRAK\s*(.*?)(?=\n\s*(?:1\.?\s+PENDAHULUAN|I\.?\s+PENDAHULUAN)\b)",
    ]

    for pattern in patterns:
        match = re.search(pattern, clean_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            abstract = re.sub(r"\s+", " ", match.group(1)).strip(" :-\n")
            if len(abstract) > 40:
                return abstract

    fallback = re.sub(r"\s+", " ", clean_text).strip()
    return fallback[:650] + ("..." if len(fallback) > 650 else "")


def highlight_text(text: str, query: str) -> str:
    """Melakukan highlight pada kata kunci query di dalam teks secara aman (anti-XSS)."""
    if not text or not query:
        return html.escape(str(text))

    clean_q = query.strip().strip("\"'")
    tokens = [t.strip("*?\"'") for t in clean_q.split() if t.strip("*?\"'")]
    if not tokens:
        return html.escape(str(text))

    escaped_text = html.escape(str(text))

    # Gabungkan frasa utuh (jika multi-kata) + tiap kata unik, urutkan dari terpanjang
    targets = set(tokens)
    if len(tokens) > 1:
        targets.add(clean_q)
    sorted_targets = sorted(targets, key=len, reverse=True)

    pattern = re.compile(
        r"(" + "|".join(re.escape(t) for t in sorted_targets) + r")",
        flags=re.IGNORECASE,
    )

    return pattern.sub(
        r'<mark style="background-color: #fed7aa; color: #1e293b; '
        r'padding: 0.08rem 0.25rem; border-radius: 4px; font-weight: 700;">\1</mark>',
        escaped_text,
    )


def search_articles(
    query: str,
    retrieval: InformationRetrieval,
    model: Any,
    document_vectors: dict,
    corpus: pd.DataFrame,
    top_limit: int = 500,
) -> tuple[list[dict], float, list[str]]:
    """Menjalankan retrieval, ekspansi wildcard, cosine similarity, dan ranking."""
    start = time.perf_counter()
    query_tokens = normalize_query(query)

    if not query_tokens:
        return [], 0.0, []

    normalized_query = " ".join(query_tokens)
    retrieval_result = retrieval.search(normalized_query)

    candidate_ids = set(retrieval_result["documents"].keys())
    expanded_terms: list[str] = []

    for token in query_tokens:
        if "*" in token or "?" in token:
            expanded_terms.extend(retrieval.wildcard_search(token))
        elif token in retrieval.dictionary:
            expanded_terms.append(token)

    expanded_terms = list(dict.fromkeys(expanded_terms))
    if not candidate_ids or not expanded_terms:
        return [], time.perf_counter() - start, expanded_terms

    query_vector = model.transform_query(expanded_terms)
    if not query_vector:
        return [], time.perf_counter() - start, expanded_terms

    phrase_mode = query.strip().startswith('"') and query.strip().endswith('"')
    phrase = " ".join(query_tokens)

    corpus_by_id = corpus.set_index("id", drop=False)
    if phrase_mode:
        candidate_ids = {
            doc_id
            for doc_id in candidate_ids
            if doc_id in corpus_by_id.index
            and phrase in " ".join(str(corpus_by_id.loc[doc_id, "processed_text"]).split())
        }

    ranked = []
    query_norm = sum(weight * weight for weight in query_vector.values()) ** 0.5

    for doc_id in candidate_ids:
        vector = document_vectors.get(str(doc_id))
        if not vector:
            continue

        dot = sum(
            weight * vector.get(term, 0.0) for term, weight in query_vector.items()
        )
        doc_norm = sum(weight * weight for weight in vector.values()) ** 0.5
        score = dot / (query_norm * doc_norm) if query_norm and doc_norm else 0.0

        if score > 0 and doc_id in corpus_by_id.index:
            row = corpus_by_id.loc[doc_id]
            ranked.append({
                "id": str(doc_id),
                "title": row.get("title", "Judul tidak tersedia"),
                "authors": row.get("authors", "Penulis tidak tersedia"),
                "year": int(row["year"]) if pd.notna(row.get("year")) else None,
                "score": float(score),
                "abstract": extract_abstract(row.get("text", "")),
                "pdf_url": row.get("pdf_url", ""),
                "article_url": row.get("article_url", ""),
                "filename": row.get("filename", ""),
            })

    ranked.sort(key=lambda item: item["score"], reverse=True)
    elapsed = time.perf_counter() - start
    return ranked[:top_limit], elapsed, expanded_terms


# ==============================================================================
# FUNGSI PENYIMPANAN & PERHITUNGAN METRIK EVALUASI
# ==============================================================================

def load_evaluations() -> dict[str, Any]:
    """Membaca data penilaian relevansi yang tersimpan di JSON."""
    if EVAL_FILE.exists():
        try:
            with open(EVAL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_evaluations(data: dict[str, Any]) -> None:
    """Menyimpan data penilaian relevansi ke file JSON."""
    with open(EVAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def compute_metrics_table(evaluations: dict[str, Any]) -> tuple[pd.DataFrame, float]:
    """Menghitung Precision@K, Recall@K, F1-Score, AP, dan MAP dari data evaluasi."""
    rows = []
    aps = []

    for query_key, record in evaluations.items():
        judgments = [int(item["relevant"]) for item in record.get("items", [])]
        k = len(judgments)
        if k == 0:
            continue

        rel_retrieved = sum(judgments)
        total_rel_corpus = int(record.get("total_relevant_in_corpus", rel_retrieved))
        # Pastikan pembagi recall tidak lebih kecil dari relevan yang ditemukan
        effective_total_rel = max(total_rel_corpus, rel_retrieved)

        precision = rel_retrieved / k
        recall = rel_retrieved / effective_total_rel if effective_total_rel > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Average Precision (AP)
        running_rel = 0
        sum_prec = 0.0
        for idx, is_rel in enumerate(judgments):
            if is_rel == 1:
                running_rel += 1
                sum_prec += running_rel / (idx + 1)

        ap = sum_prec / effective_total_rel if effective_total_rel > 0 else 0.0
        aps.append(ap)

        rows.append({
            "Query": record.get("query", query_key),
            "K (Dinilai)": k,
            "Relevan Ditemukan": rel_retrieved,
            "Total Relevan di Korpus": effective_total_rel,
            "Precision@K": round(precision, 4),
            "Recall@K": round(recall, 4),
            "F1-Score": round(f1, 4),
            "Average Precision (AP)": round(ap, 4),
            "Waktu Simpan": record.get("timestamp", "-"),
        })

    df = pd.DataFrame(rows)
    mean_ap = sum(aps) / len(aps) if aps else 0.0
    return df, mean_ap


# ==============================================================================
# HALAMAN EVALUASI SISTEM
# ==============================================================================

def render_evaluation_page():
    st.markdown('<div class="main-title">📊 Evaluasi Kualitas Pencarian (IR Metrics)</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Rekapitulasi Precision@K, Recall@K, F1-Score, Average Precision (AP), dan MAP</div>',
        unsafe_allow_html=True,
    )

    evaluations = load_evaluations()
    if not evaluations:
        st.info(
            "Belum ada data penilaian yang tersimpan. Silakan buka halaman **🔎 Pencarian Artikel**, "
            "aktifkan **Mode Evaluasi Relevansi** pada sidebar, nilai artikel hasil pencarian, lalu klik **Simpan Penilaian Evaluasi**."
        )
        return

    df_metrics, mean_ap = compute_metrics_table(evaluations)

    # Ringkasan Metrik Utama
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Jumlah Query Diuji", len(df_metrics))
    c2.metric("Rata-rata Precision@K", f"{df_metrics['Precision@K'].mean():.4f}")
    c3.metric("Rata-rata Recall@K", f"{df_metrics['Recall@K'].mean():.4f}")
    c4.metric("Mean Average Precision (MAP)", f"{mean_ap:.4f}")

    st.divider()
    st.subheader("Tabel Hasil Evaluasi Per Query")
    st.dataframe(df_metrics, use_container_width=True, hide_index=True)

    # Ekspor ke CSV
    col_dl, col_del = st.columns([2, 1])
    with col_dl:
        csv_data = df_metrics.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Unduh Hasil Evaluasi (CSV)",
            data=csv_data,
            file_name=f"evaluasi_jupita_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            type="primary",
        )

    # Detail per query & opsi hapus
    with st.expander("Lihat Detail Penilaian Per Artikel & Kelola Data"):
        selected_q = st.selectbox("Pilih Query untuk melihat detail:", list(evaluations.keys()))
        if selected_q:
            rec = evaluations[selected_q]
            st.write(f"**Query:** `{rec['query']}` | **Total Relevan di Korpus:** `{rec['total_relevant_in_corpus']}`")
            detail_df = pd.DataFrame(rec["items"])
            detail_df["Status"] = detail_df["relevant"].map({1: "✅ Relevan", 0: "❌ Tidak Relevan"})
            st.dataframe(
                detail_df[["rank", "doc_id", "title", "score", "Status"]],
                use_container_width=True,
                hide_index=True,
            )
            if st.button(f"🗑️ Hapus Evaluasi Query '{selected_q}'", type="secondary"):
                del evaluations[selected_q]
                save_evaluations(evaluations)
                st.success(f"Data evaluasi untuk '{selected_q}' telah dihapus.")
                st.rerun()


# ==============================================================================
# APLIKASI UTAMA
# ==============================================================================

def main():
    with st.sidebar:
        st.header("Navigasi")
        page = st.radio(
            "Pilih Halaman",
            ["🔎 Pencarian Artikel", "📊 Evaluasi Sistem (IR Metrics)"],
            label_visibility="collapsed",
        )
        st.divider()

    if page == "📊 Evaluasi Sistem (IR Metrics)":
        render_evaluation_page()
        return

    st.markdown('<div class="main-title">🔎 JUPITA Search Engine</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Mesin pencarian artikel Jurnal Pengabdian Informatika</div>',
        unsafe_allow_html=True,
    )

    try:
        retrieval, model, document_vectors, corpus = load_resources()
    except Exception as exc:
        st.error(f"Gagal memuat komponen pencarian: {exc}")
        st.info(
            "Pastikan file index dan model TF-IDF sudah dibuat. Jalankan aplikasi "
            "dari folder project dengan perintah: streamlit run app.py"
        )
        st.stop()

    with st.sidebar:
        st.header("Pengaturan Evaluasi")
        eval_mode = st.toggle(
            "Mode Evaluasi Relevansi (Manual Judgment)",
            value=False,
            help="Aktifkan untuk menilai Relevan / Tidak Relevan langsung pada hasil pencarian teratas.",
        )
        top_k_eval = st.radio(
            "Jumlah Artikel Dinilai (Top-K)",
            options=[10, 20],
            index=0,
            disabled=not eval_mode,
            horizontal=True,
        )

        st.divider()
        st.header("Filter Pencarian")
        selected_years = st.multiselect(
            "Tahun publikasi",
            options=list(range(2022, 2027)),
            default=list(range(2022, 2027)),
            help="Pilih satu atau beberapa tahun publikasi.",
        )
        page_size = st.selectbox("Jumlah hasil per halaman", [5, 10, 20], index=1)
        st.divider()
        st.caption(f"Jumlah artikel dalam koleksi: {len(corpus):,}")
        st.caption("Rentang tahun koleksi: 2022–2026")

    with st.form("search_form"):
        query = st.text_input(
            "Masukkan kata kunci",
            placeholder='Contoh: sistem informasi desa atau "perancangan ulang website"',
            help='Gunakan tanda kutip untuk pencarian frasa, misalnya "sistem informasi".',
        )
        submitted = st.form_submit_button(
            "Cari Artikel", type="primary", use_container_width=True
        )

    if submitted:
        if not query.strip():
            st.warning("Query masih kosong. Masukkan kata kunci terlebih dahulu.")
            st.session_state.pop("search_results", None)
            st.session_state.pop("search_query", None)
        else:
            with st.spinner("Mencari artikel yang relevan..."):
                results, elapsed, matched_terms = search_articles(
                    query,
                    retrieval,
                    model,
                    document_vectors,
                    corpus,
                )
            st.session_state["search_results"] = results
            st.session_state["search_query"] = query
            st.session_state["search_time"] = elapsed
            st.session_state["matched_terms"] = matched_terms
            st.session_state["current_page"] = 1

    if "search_results" not in st.session_state:
        st.markdown("### Mulai pencarian")
        st.write(
            "Masukkan kata kunci untuk menemukan artikel. Kamu juga dapat menggunakan "
            "wildcard seperti `sistem*` atau pencarian frasa dengan tanda kutip."
        )
        return

    results = st.session_state["search_results"]
    active_query = st.session_state.get("search_query", "")
    elapsed = st.session_state.get("search_time", 0.0)
    matched_terms = st.session_state.get("matched_terms", [])

    filtered_results = [
        item for item in results if item["year"] in selected_years
    ]

    st.markdown(f"### Hasil pencarian: `{active_query}`")
    col1, col2, col3 = st.columns(3)
    col1.metric("Artikel ditemukan", len(filtered_results))
    col2.metric("Waktu pencarian", f"{elapsed:.4f} detik")
    col3.metric("Term cocok", len(matched_terms))

    if matched_terms:
        st.caption("Term yang cocok: " + ", ".join(matched_terms[:30]))

    if not selected_years:
        st.warning("Pilih minimal satu tahun publikasi pada filter.")
        return

    if not filtered_results:
        st.warning("Tidak ditemukan artikel yang sesuai dengan query dan filter tahun.")
        return

    # ==========================================================================
    # MODE EVALUASI RELEVANSI (TOP-K LANGSUNG DI GUI)
    # ==========================================================================
    if eval_mode:
        st.info(
            f"📋 **Mode Evaluasi Aktif (Top-{top_k_eval})**: Berikan penilaian **Relevan** atau **Tidak Relevan** "
            f"pada artikel di bawah ini, lalu tekan tombol **Simpan Penilaian Evaluasi** di bagian bawah."
        )

        eval_candidates = filtered_results[:top_k_eval]
        saved_evals = load_evaluations()
        existing_record = saved_evals.get(active_query.strip().lower(), {})
        existing_map = {
            item["doc_id"]: item["relevant"]
            for item in existing_record.get("items", [])
        }

        judgments_buffer = []

        for rank, item in enumerate(eval_candidates, start=1):
            highlighted_title = highlight_text(item["title"], active_query)
            highlighted_abstract = highlight_text(item["abstract"], active_query)

            with st.container(border=True):
                st.markdown(f"**{rank}. {highlighted_title}**", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='result-meta'>"
                    f"{html.escape(str(item['authors'] or 'Penulis tidak tersedia'))} &bull; "
                    f"{item['year'] or 'Tahun tidak tersedia'} &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"Skor Relevansi: <span class='score-badge'>{item['score']:.4f}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<p style='text-align: justify; line-height: 1.6;'>{highlighted_abstract}</p>",
                    unsafe_allow_html=True,
                )

                default_idx = 0 if existing_map.get(item["id"], 1) == 1 else 1
                choice = st.radio(
                    f"Penilaian Artikel #{rank}",
                    options=["Relevan", "Tidak Relevan"],
                    index=default_idx,
                    key=f"eval_{active_query}_{item['id']}_{rank}",
                    horizontal=True,
                )

                judgments_buffer.append({
                    "rank": rank,
                    "doc_id": item["id"],
                    "title": item["title"],
                    "score": round(item["score"], 6),
                    "relevant": 1 if choice == "Relevan" else 0,
                })

        st.divider()
        with st.container(border=True):
            st.subheader("Simpan Hasil Evaluasi Query Ini")
            rel_now = sum(x["relevant"] for x in judgments_buffer)
            st.write(f"Jumlah dinilai relevan saat ini: **{rel_now} dari {len(judgments_buffer)}** artikel.")

            default_total_corpus = existing_record.get("total_relevant_in_corpus", max(rel_now, 1))
            total_in_corpus = st.number_input(
                "Total dokumen relevan yang ada di seluruh korpus untuk query ini (Ground Truth Recall):",
                min_value=max(rel_now, 1),
                value=max(int(default_total_corpus), rel_now, 1),
                step=1,
                help="Diperlukan sebagai pembagi untuk menghitung Recall@K dan Average Precision (AP).",
            )

            if st.button("💾 Simpan Penilaian Evaluasi", type="primary", use_container_width=True):
                q_key = active_query.strip().lower()
                saved_evals[q_key] = {
                    "query": active_query.strip(),
                    "k": len(judgments_buffer),
                    "total_relevant_in_corpus": int(total_in_corpus),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "items": judgments_buffer,
                }
                save_evaluations(saved_evals)
                st.success(
                    f"✅ Penilaian untuk query **'{active_query}'** berhasil disimpan! "
                    "Buka halaman **📊 Evaluasi Sistem (IR Metrics)** di sidebar untuk melihat tabel hasil dan ekspor CSV."
                )
        return

    # ==========================================================================
    # MODE PENCARIAN NORMAL (DENGAN PAGINATION & HIGHLIGHT)
    # ==========================================================================
    total_pages = max(1, (len(filtered_results) + page_size - 1) // page_size)
    current_page = min(st.session_state.get("current_page", 1), total_pages)

    nav_left, nav_mid, nav_right = st.columns([1, 2, 1])
    with nav_left:
        if st.button(
            "← Sebelumnya",
            disabled=current_page <= 1,
            use_container_width=True,
        ):
            st.session_state["current_page"] = current_page - 1
            st.rerun()
    with nav_mid:
        st.markdown(
            f"<div style='text-align:center;padding-top:.45rem'>Halaman "
            f"<b>{current_page}</b> dari <b>{total_pages}</b></div>",
            unsafe_allow_html=True,
        )
    with nav_right:
        if st.button(
            "Berikutnya →",
            disabled=current_page >= total_pages,
            use_container_width=True,
        ):
            st.session_state["current_page"] = current_page + 1
            st.rerun()

    start_idx = (current_page - 1) * page_size
    page_results = filtered_results[start_idx:start_idx + page_size]

    for rank, item in enumerate(page_results, start=start_idx + 1):
        highlighted_title = highlight_text(item["title"], active_query)
        highlighted_abstract = highlight_text(item["abstract"], active_query)

        with st.container(border=True):
            st.markdown(f"**{rank}. {highlighted_title}**", unsafe_allow_html=True)
            st.markdown(
                f"<div class='result-meta'>"
                f"{html.escape(str(item['authors'] or 'Penulis tidak tersedia'))} &bull; "
                f"{item['year'] or 'Tahun tidak tersedia'} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"Skor Relevansi: <span class='score-badge'>{item['score']:.4f}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<p style='text-align: justify; line-height: 1.6;'>{highlighted_abstract}</p>",
                unsafe_allow_html=True,
            )

            with st.expander("Lihat detail artikel"):
                st.write(f"**Judul:** {item['title']}")
                st.write(f"**Penulis:** {item['authors']}")
                st.write(f"**Tahun:** {item['year']}")
                st.write(f"**Skor cosine similarity:** {item['score']:.6f}")
                if item["article_url"]:
                    st.markdown(f"[Buka halaman artikel]({item['article_url']})")
                if item["pdf_url"]:
                    st.link_button("Buka / Unduh PDF", item["pdf_url"])
                else:
                    st.info("URL PDF tidak tersedia pada metadata.")


if __name__ == "__main__":
    main()