"""
mengubah kumpulan teks menjadi index yang menunjukkan kata tertentu muncul pada dokumen mana dan berapa kali.
"""
import pandas as pd
import json
import time
from pathlib import Path
from collections import defaultdict, Counter

INPUT_PATH = Path("processed/preprocessed_documents.csv")
INDEX_DIR = Path("index")
BLOCK_DIR = INDEX_DIR / "blocks"

BLOCK_SIZE = 50

INDEX_DIR.mkdir(exist_ok=True)
BLOCK_DIR.mkdir(exist_ok=True)

# Load preprocessed documents
df = pd.read_csv(INPUT_PATH)
df["processed_text"] = df["processed_text"].fillna("")

if df["id"].duplicated().any():
    raise ValueError("Duplicate document IDs found")

print("Total documents:", len(df))

# Build an index block
def build_block(documents):
    block = defaultdict(dict)

    for doc in documents:
        doc_id = str(doc["id"])
        tokens = doc["processed_text"].split()
        term_counts = Counter(tokens)

        for term, frequency in term_counts.items():
            block[term][doc_id] = frequency

    return dict(sorted(block.items()))

# Save an index block
def save_block(block, block_id):
    filepath = BLOCK_DIR / f"block_{block_id:03d}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(block, f, ensure_ascii=False)

    return filepath

# Build index using SPIMI blocks
start_time = time.perf_counter()
block_files = []

documents = df[["id", "processed_text"]].to_dict("records")

for start in range(0, len(documents), BLOCK_SIZE):
    batch = documents[start:start + BLOCK_SIZE]
    block = build_block(batch)

    block_id = len(block_files) + 1
    filepath = save_block(block, block_id)

    block_files.append(filepath)
    print(f"Block {block_id} saved: {len(block)} terms")

# Merge index blocks
merged_index = defaultdict(dict)

for filepath in block_files:
    with open(filepath, "r", encoding="utf-8") as f:
        block = json.load(f)

    for term, postings in block.items():
        merged_index[term].update(postings)

final_index = {
    term: dict(sorted(
        postings.items(),
        key=lambda item: int(item[0])
    ))
    for term, postings in sorted(merged_index.items())
}

# Save final inverted index
with open(INDEX_DIR / "inverted_index.json", "w", encoding="utf-8") as f:
    json.dump(final_index, f, ensure_ascii=False)

# Save term dictionary
dictionary = {
    term: {
        "document_frequency": len(postings),
        "collection_frequency": sum(postings.values())
    }
    for term, postings in final_index.items()
}

with open(INDEX_DIR / "dictionary.json", "w", encoding="utf-8") as f:
    json.dump(dictionary, f, ensure_ascii=False)

elapsed = time.perf_counter() - start_time

print("\nIndexing completed")
print("Total documents:", len(df))
print("Total blocks:", len(block_files))
print("Unique terms:", len(final_index))
print(f"Indexing time: {elapsed:.3f} seconds")

# Display sample posting lists
for term in list(final_index)[:5]:
    print(term, final_index[term])