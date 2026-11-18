
import pandas as pd
import shutil
import re
from pathlib import Path

DATASET_DIR = Path("dataset")
PROCESSED_DIR = Path("processed")
EXCLUDED_DIR = Path("excluded")

EXCLUDED_DIR.mkdir(exist_ok=True)

# Load datasets
metadata = pd.read_csv(DATASET_DIR / "metadata.csv")
documents = pd.read_csv(PROCESSED_DIR / "documents.csv")
preprocessed = pd.read_csv(
    PROCESSED_DIR / "preprocessed_documents.csv"
)

# Define non-article title patterns
EXCLUDE_PATTERNS = [
    r"^cover(?:\s|$)",
    r"^susunan\s+dewan\s+redaksi",
    r"^daftar\s+isi",
    r"^table\s+of\s+contents",
    r"^dewan\s+redaksi",
    r"^editorial(?:\s|$)",
    r"^kata\s+pengantar",
    r"^halaman\s+judul"
]

def is_non_article(title):
    if pd.isna(title):
        return False

    title = re.sub(r"\s+", " ", str(title)).strip().lower()

    return any(
        re.search(pattern, title)
        for pattern in EXCLUDE_PATTERNS
    )

# Identify non-article documents
metadata["is_non_article"] = metadata["title"].apply(
    is_non_article
)

excluded = metadata[metadata["is_non_article"]].copy()

valid_metadata = metadata[
    ~metadata["is_non_article"]
].copy()

# Keep only successfully downloaded documents
valid_metadata = valid_metadata[
    valid_metadata["status"] == "Success"
].copy()

# Filter extracted and preprocessed documents
valid_ids = set(valid_metadata["id"])

clean_documents = documents[
    documents["id"].isin(valid_ids)
].copy()

clean_preprocessed = preprocessed[
    preprocessed["id"].isin(valid_ids)
].copy()

# Exclude empty processed text
clean_preprocessed = clean_preprocessed[
    clean_preprocessed["processed_text"].notna()
    & (
        clean_preprocessed["processed_text"]
        .astype(str)
        .str.strip() != ""
    )
].copy()

# Keep metadata consistent with the final corpus
final_ids = set(clean_preprocessed["id"])

clean_documents = clean_documents[
    clean_documents["id"].isin(final_ids)
].copy()

valid_metadata = valid_metadata[
    valid_metadata["id"].isin(final_ids)
].copy()

# Save clean datasets
valid_metadata.drop(
    columns=["is_non_article"]
).to_csv(
    DATASET_DIR / "metadata_articles.csv",
    index=False,
    encoding="utf-8-sig"
)

clean_documents.to_csv(
    PROCESSED_DIR / "documents_articles.csv",
    index=False,
    encoding="utf-8-sig"
)

clean_preprocessed.to_csv(
    PROCESSED_DIR / "preprocessed_articles.csv",
    index=False,
    encoding="utf-8-sig"
)

excluded.drop(
    columns=["is_non_article"]
).to_csv(
    EXCLUDED_DIR / "excluded_documents.csv",
    index=False,
    encoding="utf-8-sig"
)

# Move non-article PDF files
moved = 0

for _, row in excluded.iterrows():
    filename = row["filename"]

    if pd.isna(filename):
        continue

    source = DATASET_DIR / str(filename)
    destination = EXCLUDED_DIR / str(filename)

    if source.exists():
        if destination.exists():
            print(f"Already exists: {filename}")
            continue

        shutil.move(str(source), str(destination))
        moved += 1

# Display results
print("\nFiltering completed")
print("Original metadata:", len(metadata))
print("Excluded non-articles:", len(excluded))
print("Moved PDFs:", moved)
print("Final articles:", len(clean_preprocessed))

print("\nExcluded document titles:")
print(excluded["title"].to_string(index=False))