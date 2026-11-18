
import pandas as pd
import json
import time
from pathlib import Path
from collections import defaultdict, Counter

INPUT_PATH = Path("processed/preprocessed_articles.csv")
INDEX_DIR = Path("index")
BLOCK_DIR = INDEX_DIR / "blocks"

MAX_POSTINGS = 10000

INDEX_DIR.mkdir(exist_ok=True)
BLOCK_DIR.mkdir(exist_ok=True)

# Load documents
df = pd.read_csv(INPUT_PATH)

required_columns = {"id", "processed_text"}

if not required_columns.issubset(df.columns):
    raise ValueError("Required columns are missing")

if df["id"].isna().any() or df["id"].duplicated().any():
    raise ValueError("Invalid or duplicate document IDs")

df["processed_text"] = df["processed_text"].fillna("")

# Initialize index
block = defaultdict(dict)
block_files = []
posting_count = 0
document_lengths = {}

start_time = time.perf_counter()

# Save index block
def save_block(block, block_id):
    filepath = BLOCK_DIR / f"block_{block_id:03d}.json"

    sorted_block = {
        term: dict(sorted(
            postings.items(),
            key=lambda item: int(item[0])
        ))
        for term, postings in sorted(block.items())
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(sorted_block, f, ensure_ascii=False)

    return filepath

# Remove previous block files
for filepath in BLOCK_DIR.glob("block_*.json"):
    filepath.unlink()

# Build SPIMI blocks
for _, row in df.iterrows():
    doc_id = str(int(row["id"]))
    tokens = row["processed_text"].split()

    document_lengths[doc_id] = len(tokens)

    term_counts = Counter(tokens)

    for term, frequency in term_counts.items():
        block[term][doc_id] = frequency
        posting_count += 1

    if posting_count >= MAX_POSTINGS:
        block_id = len(block_files) + 1
        filepath = save_block(block, block_id)

        block_files.append(filepath)

        print(f"Block {block_id} saved")

        block = defaultdict(dict)
        posting_count = 0

# Save remaining block
if block:
    block_id = len(block_files) + 1
    filepath = save_block(block, block_id)
    block_files.append(filepath)

# Merge index blocks
merged_index = defaultdict(dict)

for filepath in block_files:
    with open(filepath, "r", encoding="utf-8") as f:
        current_block = json.load(f)

    for term, postings in current_block.items():
        merged_index[term].update(postings)

final_index = {
    term: dict(sorted(
        postings.items(),
        key=lambda item: int(item[0])
    ))
    for term, postings in sorted(merged_index.items())
}

# Build term dictionary
dictionary = {
    term: {
        "document_frequency": len(postings),
        "collection_frequency": sum(postings.values())
    }
    for term, postings in final_index.items()
}

# Validate posting lists
for term, postings in final_index.items():
    for doc_id, frequency in postings.items():
        assert frequency > 0
        assert doc_id in document_lengths

total_postings = sum(
    len(postings)
    for postings in final_index.values()
)

# Save inverted index
with open(INDEX_DIR / "inverted_index.json", "w", encoding="utf-8") as f:
    json.dump(final_index, f, ensure_ascii=False)

# Save dictionary
with open(INDEX_DIR / "dictionary.json", "w", encoding="utf-8") as f:
    json.dump(dictionary, f, ensure_ascii=False)

# Save document lengths
with open(INDEX_DIR / "document_lengths.json", "w", encoding="utf-8") as f:
    json.dump(document_lengths, f)

elapsed = time.perf_counter() - start_time

index_size = (
    INDEX_DIR / "inverted_index.json"
).stat().st_size

statistics = {
    "total_documents": len(df),
    "total_blocks": len(block_files),
    "unique_terms": len(dictionary),
    "total_postings": total_postings,
    "index_size_bytes": index_size,
    "indexing_time_seconds": round(elapsed, 4),
    "max_postings_per_block": MAX_POSTINGS
}

# Save statistics
with open(INDEX_DIR / "statistics.json", "w") as f:
    json.dump(statistics, f, indent=4)

print("\nIndexing completed")

for key, value in statistics.items():
    print(f"{key}: {value}")