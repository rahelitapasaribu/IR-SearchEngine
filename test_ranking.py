
import pickle
from ranking import CosineRanker

# Load model TF-IDF
with open("index/tfidf_model.pkl", "rb") as file:
    data = pickle.load(file)

model = data["model"]
document_vectors = data["document_vectors"]
metadata = data["metadata"]

# Membuat ranker
ranker = CosineRanker(
    model,
    document_vectors,
    metadata
)

# Query pengujian (term sudah dipreprocessing)
query = ["sistem", "informasi", "desa"]

# Ranking dokumen
results = ranker.rank(query, top_k=10)

print("=== COSINE SIMILARITY RANKING ===")
print("Query:", query)
print("Jumlah hasil:", len(results))

for i, result in enumerate(results, start=1):

    print(f"\nRank {i}")
    print("ID:", result["id"])
    print("Title:", result["title"])
    print("Authors:", result["authors"])
    print("Year:", result["year"])
    print("Score:", f"{result['score']:.6f}")
