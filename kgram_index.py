import json
import time
from pathlib import Path
from collections import defaultdict

INDEX_DIR = Path("index")

DICTIONARY_PATH = INDEX_DIR / "dictionary.json"
KGRAM_PATH = INDEX_DIR / "kgram_index.json"

# Panjang karakter setiap K-Gram
K = 2


def generate_kgrams(term, k=K):
    """
    Menghasilkan K-Gram dari sebuah term.

    Contoh:
    sistem -> $sistem$
    """

    term = "$" + term + "$"

    return [
        term[i:i + k]
        for i in range(len(term) - k + 1)
    ]


# Membaca dictionary
with open(DICTIONARY_PATH, "r", encoding="utf-8") as file:
    dictionary = json.load(file)

print("\nPEMBUATAN K-GRAM INDEX")
print("Total terms:", len(dictionary))
print("K-Gram length:", K)

start_time = time.perf_counter()

# Membuat K-Gram Index
kgram_index = defaultdict(set)

for term in dictionary:

    grams = generate_kgrams(term)

    for gram in grams:
        kgram_index[gram].add(term)


# Mengubah set menjadi list terurut
kgram_index = {
    gram: sorted(terms)
    for gram, terms in sorted(kgram_index.items())
}

# Menyimpan K-Gram Index
with open(KGRAM_PATH, "w", encoding="utf-8") as file:
    json.dump(
        kgram_index,
        file,
        ensure_ascii=False,
        indent=4
    )

elapsed = time.perf_counter() - start_time

# Statistik
total_kgrams = len(kgram_index)

total_relationships = sum(
    len(terms)
    for terms in kgram_index.values()
)

print("\nK-GRAM INDEX COMPLETED")
print("Unique terms:", len(dictionary))
print("Unique K-Grams:", total_kgrams)
print("Total K-Gram relationships:", total_relationships)
print(f"Indexing time: {elapsed:.6f} seconds")

print("\nContoh K-Gram:")
for gram, terms in list(kgram_index.items())[:10]:
    print(gram, ":", terms)
