# JUPITA Search Engine

Mesin pencarian artikel jurnal JUPITA berbasis Information Retrieval. Aplikasi ini menyediakan antarmuka pencarian artikel, wildcard query, ranking TF-IDF menggunakan cosine similarity, serta evaluasi manual relevansi dengan metrik IR.

## Fitur

- Scraping metadata dan PDF artikel JUPITA
- Ekstraksi dan preprocessing teks PDF
- Pembangunan inverted index dengan SPIMI
- Dictionary blocking dan K-Gram index
- Kompresi posting list menggunakan Variable Byte Encoding (VBE)
- Pencarian wildcard dengan `*` dan `?`
- Ranking dokumen dengan TF-IDF dan cosine similarity
- Filter hasil berdasarkan tahun publikasi
- Highlight kata kunci pada judul dan abstrak
- Evaluasi manual relevansi beserta Precision, Recall, AP, dan MRR
- Tampilan interaktif berbasis Streamlit

## Teknologi

- Python
- Streamlit
- Pandas
- Beautiful Soup
- PyMuPDF
- Sastrawi
- Requests

## Struktur Project

```text
IR-SearchEngine/
├── app.py                         # Aplikasi utama Streamlit
├── scraping.py                    # Pengambilan metadata dan PDF
├── audit_data.py                  # Pemeriksaan dataset dan duplikasi
├── extract_text.py                # Ekstraksi teks dari PDF
├── preprocess.py                  # Cleaning, stopword removal, dan stemming
├── filter_articles.py             # Pemfilteran artikel dan dokumen non-artikel
├── indexing.py                    # Pembangunan SPIMI inverted index
├── evaluate_spimi.py              # Validasi SPIMI inverted index
├── dictionary_blocking.py         # Pengelompokan term dalam dictionary blok
├── kgram_index.py                 # Pembangunan K-Gram index
├── variable_byte_encoding.py      # Encoding dan decoding posting list
├── retrieval.py                   # Proses pencarian dan wildcard search
├── build_tfidf.py                 # Pembangunan model TF-IDF
├── tfidf.py                       # Implementasi TF-IDF
├── ranking.py                     # Cosine similarity ranking
├── test_tfidf.py                  # Pengujian dasar TF-IDF
├── test_ranking.py                # Pengujian cosine similarity ranking
├── test_wildcard.py               # Pengujian wildcard dan VBE
├── requirements.txt
├── dataset/                       # PDF, metadata, dan data artikel
├── processed/                     # Teks hasil ekstraksi dan preprocessing
├── index/                         # Dictionary, inverted index, model, dan index pendukung
├── cek_data/                      # Hasil audit dataset
└── excluded/                      # Dokumen non-artikel
```

## Persyaratan

- Python 3.10 atau lebih baru direkomendasikan
- `pip`
- Koneksi internet saat melakukan scraping

## Instalasi

```bash
git clone <URL_REPOSITORY>
cd IR-SearchEngine
python -m venv .venv
```

Aktifkan virtual environment:

**Windows**

```powershell
.venv\Scripts\activate
```

**Linux/macOS**

```bash
source .venv/bin/activate
```

Instal dependensi:

```bash
python -m pip install -r requirements.txt
```

## Menjalankan Aplikasi

Pastikan folder `dataset`, `processed`, dan `index` sudah berisi file hasil pemrosesan.

```bash
streamlit run app.py
```

Buka alamat yang ditampilkan Streamlit, biasanya `http://localhost:8501`.

## Membangun Data dan Index

Jalankan perintah berikut dari folder project dan urutkan sesuai alur:

```bash
# 1. Scraping metadata dan PDF
python scraping.py

# 2. Audit dataset
python audit_data.py

# 3. Ekstraksi teks PDF
python extract_text.py

# 4. Preprocessing teks
python preprocess.py

# 5. Menyaring artikel valid
python filter_articles.py

# 6. Membangun SPIMI inverted index
python indexing.py

# 7. Membangun K-Gram index
python kgram_index.py

# 8. Membangun Variable Byte Encoding
python variable_byte_encoding.py

# 9. Membangun model TF-IDF
python build_tfidf.py
```

## Pengujian

Validasi index SPIMI:

```bash
python evaluate_spimi.py
```

Pengujian TF-IDF dan cosine ranking:

```bash
python test_tfidf.py
python test_ranking.py
```

Pengujian pencarian wildcard dan posting VBE:

```bash
python test_wildcard.py
```

## Penggunaan Pencarian

Contoh query:

```text
sistem informasi desa
teknologi*
*digital*
d?gital
```

- Kata biasa dicocokkan dengan term pada inverted index.
- `*` mencocokkan bagian term yang tidak diketahui panjangnya.
- `?` mencocokkan tepat satu karakter.
- Hasil ditampilkan dan diurutkan berdasarkan skor cosine similarity.

## Evaluasi

Pada halaman pencarian, aktifkan **Mode Evaluasi Relevansi** untuk menilai hasil Top-10 atau Top-20. Penilaian disimpan ke `evaluation_judgments.json`.

Buka halaman **Evaluasi Sistem (IR Metrics)** untuk melihat metrik, termasuk:

- Precision
- Recall
- Average Precision
- Mean Reciprocal Rank
- Precision@K
- Recall@K
