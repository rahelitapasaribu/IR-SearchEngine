import json
import re
import time
import fnmatch
from pathlib import Path
from collections import defaultdict

INDEX_DIR = Path("index")

DICTIONARY_PATH = INDEX_DIR / "dictionary.json"
INVERTED_INDEX_PATH = INDEX_DIR / "inverted_index.json"
KGRAM_PATH = INDEX_DIR / "kgram_index.json"

K = 2


class InformationRetrieval:

    def __init__(self):

        # Membaca dictionary
        with open(DICTIONARY_PATH, "r", encoding="utf-8") as file:
            self.dictionary = json.load(file)

        # Membaca inverted index
        with open(INVERTED_INDEX_PATH, "r", encoding="utf-8") as file:
            self.inverted_index = json.load(file)

        # Membaca K-Gram Index
        with open(KGRAM_PATH, "r", encoding="utf-8") as file:
            self.kgram_index = json.load(file)


    def normalize_query(self, query):
        """
        Membersihkan query tanpa memecah pola wildcard.
        """

        query = query.lower().strip()

        query = re.sub(r"[^a-z0-9_*?\s]", " ", query)

        return query.split()


    def generate_kgrams(self, term):
        """
        Menghasilkan K-Gram dari term.
        """

        term = "$" + term + "$"

        return [
            term[i:i + K]
            for i in range(len(term) - K + 1)
        ]



    def get_candidates(self, pattern):

        literal_parts = [
            part for part in re.split(r"[*?]+", pattern)
            if part
        ]

        gram_sets = []

        for part in literal_parts:

            # Karakter underscore tidak terdapat
            # dalam dictionary hasil preprocessing.
            if not re.fullmatch(r"[a-z0-9]+", part):
                return set()

            grams = self.generate_kgrams(part)

            # Abaikan gram batas untuk wildcard
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

        if not gram_sets:
            return set(self.dictionary.keys())

        candidates = gram_sets[0]

        for gram_set in gram_sets[1:]:
            candidates &= gram_set

        return candidates


    def wildcard_search(self, pattern):
        """
        Melakukan pencarian wildcard.
        """

        candidates = self.get_candidates(pattern)

        # Memastikan kandidat sesuai pola wildcard
        matched_terms = sorted([
            term for term in candidates
            if fnmatch.fnmatchcase(term, pattern)
        ])

        return matched_terms

    def search_term(self, term):
        """
        Mengambil posting list suatu term.
        """

        return self.inverted_index.get(term, {})

    def search(self, query):
        """
        Memproses query normal maupun wildcard.

        Hasil pencarian berupa:
        - matched_terms
        - documents
        - processing_time
        """

        start_time = time.perf_counter()

        query_terms = self.normalize_query(query)

        matched_terms = set()
        documents = defaultdict(list)

        for term in query_terms:

            # Query wildcard
            if "*" in term or "?" in term:

                terms = self.wildcard_search(term)

            # Query normal
            else:

                terms = [term] if term in self.dictionary else []

            # Mengumpulkan term yang cocok
            for matched_term in terms:

                matched_terms.add(matched_term)

                postings = self.search_term(matched_term)

                # Menghubungkan term dengan dokumen
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


# Inisialisasi sistem
if __name__ == "__main__":

    ir = InformationRetrieval()

    print("\nINFORMATION RETRIEVAL")

    while True:

        query = input("\nMasukkan query (ketik exit untuk keluar): ")

        if query.lower() == "exit":
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
            f"{result['processing_time']:.6f} seconds"
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
