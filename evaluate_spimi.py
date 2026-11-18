import json
import pandas as pd
from collections import Counter

# Load final corpus and inverted index
df = pd.read_csv("processed/preprocessed_articles.csv")

with open("index/inverted_index.json", encoding="utf-8") as f:
    inverted_index = json.load(f)

# Validate document frequencies
errors = []

for _, row in df.iterrows():
    doc_id = str(int(row["id"]))
    tokens = str(row["processed_text"]).split()
    frequencies = Counter(tokens)

    for term, frequency in frequencies.items():
        indexed_frequency = inverted_index.get(term, {}).get(doc_id, 0)

        if indexed_frequency != frequency:
            errors.append((doc_id, term, frequency, indexed_frequency))

# Display evaluation results
print("Total documents:", len(df))
print("Unique terms:", len(inverted_index))
print("Validation errors:", len(errors))

if not errors:
    print("SPIMI validation: PASSED")
else:
    print("SPIMI validation: FAILED")
    print("Sample errors:", errors[:10])