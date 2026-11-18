
from tfidf import TfidfModel


documents = {
    "D1": ["sistem", "informasi", "desa"],
    "D2": ["sistem", "informasi", "akademik"],
    "D3": ["aplikasi", "desa", "digital"]
}

model = TfidfModel()

document_vectors = model.fit_transform(documents)

print("=== DOCUMENT FREQUENCY ===")
print(model.document_frequency)

print("\n=== IDF ===")
for term, weight in model.idf.items():
    print(f"{term}: {weight:.4f}")

print("\n=== TF-IDF DOCUMENT ===")
for doc_id, vector in document_vectors.items():
    print(doc_id, vector)

query = ["sistem", "informasi", "desa"]

query_vector = model.transform_query(query)

print("\n=== QUERY VECTOR ===")
print(query_vector)
