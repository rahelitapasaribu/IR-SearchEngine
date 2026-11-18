import pandas as pd
import re
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

# Load extracted documents
df = pd.read_csv("processed/documents.csv")
df["text"] = df["text"].fillna("")

# Initialize preprocessing tools
stemmer = StemmerFactory().create_stemmer()
stopwords = set(
    StopWordRemoverFactory().get_stop_words()
)

# Preprocess text
def preprocess(text):
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)

    tokens = text.split()
    tokens = [
        token for token in tokens
        if token not in stopwords and len(token) > 2
    ]

    tokens = [stemmer.stem(token) for token in tokens]

    return " ".join(tokens)

# Process all documents
df["processed_text"] = df["text"].apply(preprocess)

# Save results
df.to_csv(
    "processed/preprocessed_documents.csv",
    index=False,
    encoding="utf-8-sig"
)

print("Preprocessing completed")
print("Total documents:", len(df))

display(df[["title", "processed_text"]].head())