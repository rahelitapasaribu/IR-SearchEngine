
import math
from collections import Counter


class TfidfModel:

    def __init__(self):
        self.n_documents = 0
        self.vocabulary = set()
        self.document_frequency = {}
        self.idf = {}
        self.document_vectors = {}

    # Menghitung TF-IDF dokumen
    def fit_transform(self, documents):

        if not documents:
            raise ValueError("Dokumen tidak boleh kosong.")

        self.n_documents = len(documents)

        # Menghitung Document Frequency (DF)
        df = Counter()

        for tokens in documents.values():
            df.update(set(tokens))

        self.document_frequency = dict(df)
        self.vocabulary = set(df.keys())

        # Menghitung Inverse Document Frequency (IDF)
        self.idf = {
            term: math.log10(self.n_documents / frequency)
            for term, frequency in self.document_frequency.items()
        }

        # Menghitung TF-IDF setiap dokumen
        self.document_vectors = {}

        for doc_id, tokens in documents.items():

            tf = Counter(tokens)

            vector = {
                term: frequency * self.idf[term]
                for term, frequency in tf.items()
                if term in self.vocabulary
            }

            self.document_vectors[doc_id] = vector

        return self.document_vectors

    # Membuat vector query
    def transform_query(self, query_tokens):

        if not self.idf:
            raise ValueError(
                "Model harus dilatih terlebih dahulu."
            )

        tf = Counter(query_tokens)

        query_vector = {
            term: frequency * self.idf[term]
            for term, frequency in tf.items()
            if term in self.vocabulary
        }

        return query_vector
