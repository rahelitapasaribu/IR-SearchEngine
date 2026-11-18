import json
import re
import time
import fnmatch
from pathlib import Path
from collections import defaultdict
from variable_byte_encoding import decode_postings


# KONFIGURASI
INDEX_DIR = Path("index")

DICTIONARY_PATH = INDEX_DIR / "dictionary.json"
KGRAM_PATH = INDEX_DIR / "kgram_index.json"

VBE_DATA_PATH = INDEX_DIR / "postings_vbe.bin"
VBE_INDEX_PATH = INDEX_DIR / "vbe_index.json"

K = 2


# INFORMATION RETRIEVAL
class InformationRetrieval:

    def __init__(self):

        # Memastikan file tersedia
        required_files = [
            DICTIONARY_PATH,
            KGRAM_PATH,
            VBE_DATA_PATH,
            VBE_INDEX_PATH
        ]

        for path in required_files:

            if not path.exists():
                raise FileNotFoundError(
                    f"File tidak ditemukan: {path}"
                )

        # Membaca dictionary
        with open(DICTIONARY_PATH, "r", encoding="utf-8") as file:
            self.dictionary = json.load(file)

        # Membaca K-Gram Index
        with open(KGRAM_PATH, "r", encoding="utf-8") as file:
            self.kgram_index = json.load(file)

        # Membaca VBE Index
        with open(VBE_INDEX_PATH, "r", encoding="utf-8") as file:
            self.vbe_index = json.load(file)

        self.vbe_data_path = VBE_DATA_PATH


    # NORMALISASI QUERY
    def normalize_query(self, query):
        query = query.lower().strip()
        query = re.sub(
            r"[^a-z0-9_*?\s]",
            " ",
            query
        )
        return query.split()


    # GENERATE K-GRAM
    def generate_kgrams(self, term):
        term = "$" + term + "$"
        return [
            term[i:i + K]
            for i in range(len(term) - K + 1)
        ]


    # MENCARI KANDIDAT
    def get_candidates(self, pattern):

        literal_parts = [
            part
            for part in re.split(r"[*?]+", pattern)
            if part
        ]

        gram_sets = []

        for part in literal_parts:

            if not re.fullmatch(r"[a-z0-9]+", part):
                return set()

            grams = self.generate_kgrams(part)

            # Mengabaikan K-Gram batas
            grams = [
                gram for gram in grams
                if "$" not in gram
            ]

            for gram in grams:

                if gram not in self.kgram_index:
                    return set()

                gram_sets.append(
                    set(self.kgram_index[gram])
                )

        # Pola hanya wildcard
        if not gram_sets:
            return set(self.dictionary.keys())

        # Irisan kandidat
        candidates = gram_sets[0]

        for gram_set in gram_sets[1:]:
            candidates &= gram_set

        return candidates


    # WILDCARD SEARCH
    def wildcard_search(self, pattern):
        candidates = self.get_candidates(pattern)
        matched_terms = sorted([
            term
            for term in candidates
            if fnmatch.fnmatchcase(term, pattern)
        ])

        return matched_terms


    # MENGAMBIL POSTING LIST VBE
    def search_term(self, term):

        if term not in self.vbe_index:
            return {}

        # Mengambil offset dan panjang byte
        offset, byte_length = self.vbe_index[term]

        # Membaca data binary
        with open(self.vbe_data_path, "rb") as binary_file:
            binary_file.seek(offset)
            encoded_data = binary_file.read(byte_length)

        if len(encoded_data) != byte_length:
            raise ValueError(
                f"Data VBE tidak lengkap: {term}"
            )

        # Memanggil fungsi decoding milik rekan
        postings = decode_postings(encoded_data)

        return postings


    # PENCARIAN QUERY
    def search(self, query):
        start_time = time.perf_counter()
        query_terms = self.normalize_query(query)
        matched_terms = set()
        documents = defaultdict(list)

        for term in query_terms:
            # Pencarian wildcard
            if "*" in term or "?" in term:
                terms = self.wildcard_search(term)
            # Pencarian normal
            else:
                terms = [
                    term
                ] if term in self.dictionary else []

            # Mengambil posting list
            for matched_term in terms:
                matched_terms.add(matched_term)
                postings = self.search_term(matched_term)

                for doc_id, frequency in postings.items():
                    documents[doc_id].append({
                        "term": matched_term,
                        "frequency": frequency
                    })

        elapsed = time.perf_counter() - start_time

        return {
            "query": query,
            "matched_terms": sorted(matched_terms),
            "total_matched_terms": len(matched_terms),
            "documents": dict(documents),
            "total_documents": len(documents),
            "processing_time": elapsed

        }


# MENJALANKAN SISTEM
if __name__ == "__main__":

    ir = InformationRetrieval()

    print("\nINFORMATION RETRIEVAL WITH K-GRAM AND VBE")

    while True:

        query = input(
            "\nMasukkan query (ketik exit untuk keluar): "
        )

        if query.lower().strip() == "exit":
            break

        result = ir.search(query)

        print("\nHASIL PENCARIAN")
        print("Query:", result["query"])
        print(
            "Matched terms:",
            result["matched_terms"]
        )
        print(
            "Total matched terms:",
            result["total_matched_terms"]
        )
        print(
            "Total documents:",
            result["total_documents"]
        )
        print(
            "Processing time:",
            f"{result['processing_time']:.8f} seconds"
        )
        if result["total_documents"] == 0:

            print("Tidak ditemukan dokumen yang cocok.")

        else:

            print("\nContoh hasil dokumen:")

            for doc_id, details in list(
                result["documents"].items()
            )[:10]:

                print(
                    f"Document ID: {doc_id} | "
                    f"Terms: {details}"
                )
