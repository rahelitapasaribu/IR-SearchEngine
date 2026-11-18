import json
import time
from pathlib import Path
from collections import defaultdict


INDEX_DIR = Path("index")

DICTIONARY_PATH = INDEX_DIR / "dictionary.json"
INVERTED_INDEX_PATH = INDEX_DIR / "inverted_index.json"

BLOCKED_DICTIONARY_PATH = (INDEX_DIR / "blocked_dictionary.json")
BLOCK_INDEX_PATH = (INDEX_DIR / "block_index.json")
STATISTICS_PATH = (INDEX_DIR / "blocking_statistics.json")

# Jumlah karakter prefix untuk mengelompokkan term
BLOCK_PREFIX_LENGTH = 2

# Membaca dictionary dan inverted index
print("DICTIONARY BLOCKING")

if not DICTIONARY_PATH.exists():
    raise FileNotFoundError(f"Dictionary tidak ditemukan: {DICTIONARY_PATH}")

if not INVERTED_INDEX_PATH.exists():
    raise FileNotFoundError(f"Inverted index tidak ditemukan: {INVERTED_INDEX_PATH}")

with open(DICTIONARY_PATH, "r", encoding="utf-8") as file:
    dictionary = json.load(file)

print("Dictionary berhasil dimuat")
print("Jumlah term:", len(dictionary))

# Block dictionary berdasarkan prefix
start_time = time.perf_counter()

blocks = defaultdict(dict)

for term, information in dictionary.items():
    # Mengambil dua karakter pertama dari term
    prefix = term[:BLOCK_PREFIX_LENGTH]

    # Mengelompokkan term berdasarkan prefix
    blocks[prefix][term] = information

# Mengurutkan blok berdasarkan prefix dan term
blocked_dictionary = {}

for prefix, terms in sorted(blocks.items()):

    blocked_dictionary[prefix] = {term: terms[term] for term in sorted(terms)}

# Membentuk block index untuk mempermudah pencarian term dalam blok
# Menyimpan daftar term dalam setiap blok
block_index = {}

for prefix, terms in blocked_dictionary.items():

    term_list = list(terms.keys())

    block_index[prefix] = {
        "term_count": len(term_list),
        "first_term": term_list[0],
        "last_term": term_list[-1],
        "terms": term_list
    }

# Menyimpan hasil blocking ke file JSON
with open(BLOCKED_DICTIONARY_PATH, "w", encoding="utf-8") as file:

    json.dump(blocked_dictionary, file, ensure_ascii=False, indent=4)


with open(BLOCK_INDEX_PATH, "w", encoding="utf-8") as file:

    json.dump(block_index, file, ensure_ascii=False, indent=4)

# Menghitung statistik blocking
total_terms = len(dictionary)
total_blocks = len(blocked_dictionary)

block_sizes = [len(terms) for terms in blocked_dictionary.values()]

max_terms_per_block = max(block_sizes, default=0)
min_terms_per_block = min(block_sizes, default=0)

average_terms_per_block = (total_terms / total_blocks if total_blocks > 0 else 0)

elapsed_time = time.perf_counter() - start_time

statistics = {
    "total_terms": total_terms,
    "total_blocks": total_blocks,
    "prefix_length": BLOCK_PREFIX_LENGTH,
    "average_terms_per_block": round(average_terms_per_block, 2),
    "max_terms_per_block": max_terms_per_block,
    "min_terms_per_block": min_terms_per_block,
    "blocking_time_seconds": round(elapsed_time, 6)
}

with open(STATISTICS_PATH, "w", encoding="utf-8") as file:

    json.dump(statistics, file, indent=4)

# Menampilkan hasil blocking dan statistik
print("\nHASIL DICTIONARY BLOCKING")
print("Total term       :", total_terms)
print("Total blok       :", total_blocks)
print("Prefix length    :", BLOCK_PREFIX_LENGTH)
print("Rata-rata term   :", round(average_terms_per_block, 2))
print("Term terbanyak   :", max_terms_per_block)
print("Term paling sedikit:", min_terms_per_block)

print("\nContoh isi blok:")

for prefix, terms in list(blocked_dictionary.items())[:5]:

    print(f"\nBlok '{prefix}'")
    print("Jumlah term:", len(terms))

    for term in list(terms.keys())[:5]:
        print("-", term)

# Fungsi pencarian term dalam blok
def search_term(term):

    """
    Mencari term melalui dictionary yang telah diblokir

    Tahapan:
    1. Menentukan prefix term.
    2. Mengambil blok berdasarkan prefix.
    3. Mencari term di dalam blok.
    4. Mengambil posting list dari inverted index.
    """

    term = term.lower()

    prefix = term[:BLOCK_PREFIX_LENGTH]

    # Memeriksa apakah blok tersedia
    if prefix not in blocked_dictionary:
        return None

    # Mencari term pada blok yang sesuai
    if term not in blocked_dictionary[prefix]:
        return None

    # Membaca inverted index untuk mengambil posting list
    with open(INVERTED_INDEX_PATH, "r", encoding="utf-8") as file:

        inverted_index = json.load(file)

    postings = inverted_index.get(term)

    return {
        "term": term,
        "block": prefix,
        "information": blocked_dictionary[prefix][term],
        "postings": postings
    }

# Pengujian pencarian term
print("\nPENGUJIAN PENCARIAN TERM")

test_terms = [
    "teknologi",
    "digital",
    "informasi",
    "aplikasi",
    "term_tidak_ada"
]

for term in test_terms:

    search_start = time.perf_counter()

    result = search_term(term)

    search_time = (time.perf_counter() - search_start)

    if result:

        print(f"\nTerm ditemukan : {result['term']}")
        print(f"Blok           : {result['block']}")
        print("Document Frequency:", result["information"]["document_frequency"])
        print("Collection Frequency:", result["information"]["collection_frequency"])
        print("Jumlah posting:", len(result["postings"]))

    else:

        print(f"\nTerm tidak ditemukan: {term}")

    print(f"Waktu pencarian: {search_time:.8f} detik")

# Ringkasan hasil blocking
print("\nDICTIONARY BLOCKING SELESAI")

for key, value in statistics.items():
    print(f"{key}: {value}")

print("\nFile hasil:")
print("-", BLOCKED_DICTIONARY_PATH)
print("-", BLOCK_INDEX_PATH)
print("-", STATISTICS_PATH)