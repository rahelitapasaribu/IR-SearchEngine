import json
import time
import shutil
from pathlib import Path
from bisect import bisect_right


INDEX_DIR = Path("index")

DICTIONARY_PATH = INDEX_DIR / "dictionary.json"
BLOCK_DIR = INDEX_DIR / "dictionary_blocks"
BLOCK_INDEX_PATH = INDEX_DIR / "block_index.json"

# Jumlah term dalam setiap blok
BLOCK_SIZE = 50
BLOCK_DIR.mkdir(parents=True, exist_ok=True)

# Load dictionary
with open(DICTIONARY_PATH, "r", encoding="utf-8") as file:
    dictionary = json.load(file)

# Memastikan seluruh term terurut alfabetis
sorted_terms = sorted(dictionary.keys())

print("\nDICTIONARY BLOCKING")
print("Total unique terms:", len(sorted_terms))
print("Block size:", BLOCK_SIZE)


# Menghindari file blok lama tertinggal ketika program dijalankan ulang
for old_file in BLOCK_DIR.glob("block_*.json"):
    old_file.unlink()


# Membuat blok-blok dari dictionary
block_index = []

start_time = time.perf_counter()

total_terms = len(sorted_terms)

for start in range(0, total_terms, BLOCK_SIZE):
    # Mengambil term sesuai ukuran blok
    block_terms = sorted_terms[start:start + BLOCK_SIZE]

    # Mengambil informasi term dan statistiknya
    block_data = {term: dictionary[term] for term in block_terms}

    # Nomor blok
    block_id = len(block_index) + 1

    # Nama file blok
    block_filename = f"block_{block_id:03d}.json"

    block_filepath = BLOCK_DIR / block_filename

    # Menyimpan isi blok
    with open(block_filepath, "w", encoding="utf-8") as file:
        json.dump(block_data, file, ensure_ascii=False)

    # Menyimpan informasi blok
    block_index.append({
        "block_id": block_id,
        "first_term": block_terms[0],
        "last_term": block_terms[-1],
        "term_count": len(block_terms),
        "filename": block_filename
    })

    print(
        f"Block {block_id:03d} saved | "
        f"{block_terms[0]} - {block_terms[-1]} | "
        f"{len(block_terms)} terms"
    )


# Menyimpan informasi blok ke file JSON
with open(BLOCK_INDEX_PATH, "w", encoding="utf-8") as file:
    json.dump(
        block_index,
        file,
        ensure_ascii=False,
        indent=4
    )

elapsed = time.perf_counter() - start_time


# Menampilkan ringkasan hasil blocking
total_blocks = len(block_index)

print("\nHASIL DICTIONARY BLOCKING")
print("Total terms:", total_terms)
print("Block size:", BLOCK_SIZE)
print("Total blocks:", total_blocks)

print(f"Blocking time: {elapsed:.6f} seconds")

print("\nContoh block index:")

for block in block_index[:5]:
    print(block)


# Daftar term pertama setiap blok
# Digunakan untuk menentukan blok yang harus diperiksa.
first_terms = [block["first_term"] for block in block_index]


def search_term(term):
    """
    Mencari term melalui block index

    Tahap:
    1. Menentukan blok berdasarkan first_term
    2. Membuka file blok yang sesuai
    3. Mencari term di dalam blok
    """

    term = term.lower()

    if not block_index:
        return None

    # Menentukan posisi blok menggunakan binary search
    position = bisect_right(first_terms, term) - 1

    # Term lebih kecil daripada term pertama kamus
    if position < 0:
        return None

    selected_block = block_index[position]

    # Membaca blok yang sesuai
    block_filepath = (BLOCK_DIR / selected_block["filename"])

    with open(block_filepath, "r", encoding="utf-8") as file:
        block_data = json.load(file)

    # Mengambil informasi term
    return block_data.get(term)


# Menampilkan hasil pengujian pencarian term
print("\nPENGUJIAN PENCARIAN TERM")
test_terms = [
    "aain",
    "aan",
    "teknologi",
    "pendidikan",
    "digital",
    "term_tidak_ada"
]

for term in test_terms:

    result = search_term(term)

    if result is not None:
        print(f"\nTerm: {term}")
        print("Status: Found")
        print("Information:", result)

    else:
        print(f"\nTerm: {term}")
        print("Status: Not found")


# Validasi hasil blocking
print("\nVALIDASI DICTIONARY BLOCKING")

blocked_term_count = sum(block["term_count"] for block in block_index)

print("Original dictionary terms:", total_terms)
print("Blocked dictionary terms:", blocked_term_count)

if total_terms == blocked_term_count:
    print("Validation: SUCCESS")
else:
    print("Validation: FAILED")

print("\nDictionary blocking completed")
