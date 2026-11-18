from pathlib import Path
import pandas as pd
import hashlib


DATASET_DIR = Path("dataset")

ARTIKEL_DIR = DATASET_DIR / "artikel"
METADATA_FILE = DATASET_DIR / "metadata.csv"

OUTPUT_DIR = Path("processed")
