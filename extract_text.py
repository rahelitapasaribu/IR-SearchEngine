import fitz
import pandas as pd
from pathlib import Path

DATASET_DIR = Path("dataset")
OUTPUT_DIR = Path("processed")
OUTPUT_DIR.mkdir(exist_ok=True)

metadata = pd.read_csv(DATASET_DIR / "metadata.csv")

documents = []

# Extract text from PDF files
for _, row in metadata.iterrows():
    filename = str(row["filename"])
    filepath = DATASET_DIR / filename

    if not filepath.exists():
        print(f"File not found: {filename}")
        continue

    try:
        with fitz.open(filepath) as pdf:
            text = " ".join(
                page.get_text("text")
                for page in pdf
            )

        if not text.strip():
            print(f"Empty text: {filename}")
            continue

        documents.append({
            "id": row["id"],
            "title": row["title"],
            "authors": row["authors"],
            "year": row["year"],
            "filename": filename,
            "text": text
        })

        print(f"Extracted: {filename}")

    except Exception as e:
        print(f"Error: {filename} - {e}")

# Save extracted documents
df = pd.DataFrame(documents)

df.to_csv(
    OUTPUT_DIR / "documents.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nExtraction completed")
print("Total documents:", len(df))