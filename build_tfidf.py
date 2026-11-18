
import pandas as pd
import pickle
from pathlib import Path
from tfidf import TfidfModel

# Load dataset yang sudah dipreprocessing
DATA_PATH = Path("processed/preprocessed_documents.csv")
OUTPUT_PATH = Path("index/tfidf_model.pkl")

df = pd.read_csv(DATA_PATH)
df["processed_text"] = df["processed_text"].fillna("")

# Membentuk dictionary dokumen: ID -> token
documents = {
    str(row["id"]): row["processed_text"].split()
    for _, row in df.iterrows()
}

# Membentuk TF-IDF
model = TfidfModel()
document_vectors = model.fit_transform(documents)

# Simpan model dan informasi dokumen
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

data = {
    "model": model,
    "document_vectors": document_vectors,
    "metadata": df[["id", "title", "authors", "year", "filename"]].to_dict("records")
}

with open(OUTPUT_PATH, "wb") as file:
    pickle.dump(data, file)

# Informasi hasil
print("=== TF-IDF BUILD ===")
print("Total dokumen:", model.n_documents)
print("Total vocabulary:", len(model.vocabulary))
print("Total document vectors:", len(model.document_vectors))
print("Model tersimpan:", OUTPUT_PATH)

print("\n=== CONTOH TF-IDF ===")
first_doc_id = next(iter(document_vectors))
print("Document ID:", first_doc_id)
print("Jumlah term:", len(document_vectors[first_doc_id]))

print("\nContoh 10 term:")
for term, weight in list(document_vectors[first_doc_id].items())[:10]:
    print(f"{term}: {weight:.6f}")
