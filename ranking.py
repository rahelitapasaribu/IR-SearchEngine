
import math


class CosineRanker:

    def __init__(self, tfidf_model, document_vectors, metadata):
        self.model = tfidf_model
        self.document_vectors = document_vectors

        # Metadata diubah menjadi dictionary dengan ID sebagai key
        self.metadata = {
            str(item["id"]): item
            for item in metadata
        }

    # Menghitung dot product dua sparse vector
    def dot_product(self, vector_a, vector_b):

        return sum(
            weight * vector_b.get(term, 0)
            for term, weight in vector_a.items()
        )

    # Menghitung magnitude vector
    def magnitude(self, vector):

        return math.sqrt(
            sum(weight ** 2 for weight in vector.values())
        )

    # Menghitung cosine similarity
    def cosine_similarity(self, query_vector, document_vector):

        dot = self.dot_product(
            query_vector,
            document_vector
        )

        query_magnitude = self.magnitude(query_vector)
        document_magnitude = self.magnitude(document_vector)

        if query_magnitude == 0 or document_magnitude == 0:
            return 0.0

        return dot / (query_magnitude * document_magnitude)

    # Ranking dokumen berdasarkan query
    def rank(self, query_tokens, top_k=10):

        query_vector = self.model.transform_query(query_tokens)

        scores = {}

        for doc_id, document_vector in self.document_vectors.items():

            score = self.cosine_similarity(
                query_vector,
                document_vector
            )

            if score > 0:
                scores[doc_id] = score

        # Mengurutkan berdasarkan skor terbesar
        ranked_documents = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True
        )

        results = []

        for doc_id, score in ranked_documents[:top_k]:

            doc_metadata = self.metadata.get(str(doc_id), {})

            results.append({
                "id": doc_id,
                "title": doc_metadata.get("title", ""),
                "authors": doc_metadata.get("authors", ""),
                "year": doc_metadata.get("year", ""),
                "score": score
            })

        return results
