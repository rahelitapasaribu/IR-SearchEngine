from pathlib import Path
import pandas as pd
import hashlib


# Lokasi folder 
BASE_DIR = Path(__file__).resolve().parent

DATASET_DIR = BASE_DIR / "dataset"
METADATA_PATH = DATASET_DIR / "metadata.csv"

OUTPUT_DIR = BASE_DIR / "cek_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Fungsi untuk menghitung hash file
def calculate_hash(file_path):
    """Menghitung SHA-256 untuk mendeteksi file identik"""
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()

# Fungsi untuk mengubah ukuran byte menjadi MB
def format_size(size_bytes):
    """Mengubah ukuran byte menjadi MB."""
    return round(size_bytes / (1024 * 1024), 2)

# Fungsi untuk memeriksa nama file
def check_filename(filename):
    """Memberikan indikasi awal berdasarkan nama file"""

    keywords = [
        "cover",
        "sampul",
        "daftar_isi",
        "daftar isi",
        "table_of_contents",
        "editorial",
        "kata_pengantar",
        "kata pengantar",
        "template",
        "guideline",
        "copyright",
        "author_guideline",
    ]

    filename = filename.lower()

    for keyword in keywords:
        if keyword in filename:
            return "Perlu diperiksa"

    return "Tidak terindikasi"

# Periksa apakah folder dataset dan file metadata.csv ada
print("PEMERIKSAAN DATASET ARTIKEL JUPITA")

if not DATASET_DIR.exists():
    raise FileNotFoundError(f"Folder dataset tidak ditemukan: {DATASET_DIR}")

if not METADATA_PATH.exists():
    raise FileNotFoundError(f"metadata.csv tidak ditemukan: {METADATA_PATH}")

# Mengambil seluruh file di dalam folder dataset
# metadata.csv tidak dihitung sebagai file artikel
all_files = [file for file in DATASET_DIR.iterdir() if file.is_file() and file.name.lower() != "metadata.csv"]

# Memisahkan file PDF dan file selain PDF
pdf_files = [file for file in all_files if file.suffix.lower() == ".pdf"]

other_files = [file for file in all_files if file.suffix.lower() != ".pdf"]

# Distribusi file
print("\nJUMLAH FILE DATASET")
print(f"Jumlah seluruh file       : {len(all_files)}")
print(f"Jumlah file PDF           : {len(pdf_files)}")
print(f"Jumlah file selain PDF    : {len(other_files)}")

if other_files:
    print("\nFile selain PDF:")
    for file in other_files:
        print(f"- {file.name}")

# Inventarisasi file PDF
print("\nINVENTARISASI FILE PDF")

inventory = []

for file_path in pdf_files:

    size_bytes = file_path.stat().st_size

    inventory.append({
        "nama_file": file_path.name,
        "format": file_path.suffix.lower(),
        "ukuran_byte": size_bytes,
        "ukuran_mb": format_size(size_bytes),
        "file_kosong": size_bytes == 0,
        "indikasi_nama": check_filename(file_path.stem),
    })

df_files = pd.DataFrame(inventory)

if not df_files.empty:

    print(f"Jumlah PDF kosong: {df_files['file_kosong'].sum()}")
    print("\nContoh inventaris file:")
    print(df_files.head(10).to_string(index=False))

    df_files.to_csv(OUTPUT_DIR / "inventaris_file.csv", index=False, encoding="utf-8-sig")

# Distribusi ukuran file PDF
print("\nDISTRIBUSI UKURAN FILE")

if not df_files.empty:

    print(
        f"Ukuran total PDF    : "
        f"{format_size(df_files['ukuran_byte'].sum())} MB"
)

    print(
        f"Ukuran terkecil     : "
        f"{df_files['ukuran_mb'].min()} MB"
    )

    print(
        f"Ukuran terbesar     : "
        f"{df_files['ukuran_mb'].max()} MB"
    )

    print(
        f"Rata-rata ukuran    : "
        f"{df_files['ukuran_mb'].mean():.2f} MB"
    )

# Identifikasi file yang perlu diperiksa
print("\nIDENTIFIKASI FILE YANG PERLU DIPERIKSA")

if not df_files.empty:

    suspicious_files = df_files[
        (df_files["indikasi_nama"] == "Perlu diperiksa")
        | (df_files["file_kosong"])
    ]

    print(
        f"Jumlah file terindikasi perlu diperiksa: "
        f"{len(suspicious_files)}"
    )

    if not suspicious_files.empty:
        print(
            suspicious_files[
                [
                    "nama_file",
                    "ukuran_mb",
                    "indikasi_nama",
                    "file_kosong"
                ]
            ].to_string(index=False)
        )

    suspicious_files.to_csv(
        OUTPUT_DIR / "file_perlu_diperiksa.csv",
        index=False,
        encoding="utf-8-sig"
    )

# Duplikasi file PDF
print("\nPEMERIKSAAN DUPLIKASI FILE")

hash_records = []

for file_path in pdf_files:

    hash_records.append({
        "nama_file": file_path.name,
        "hash": calculate_hash(file_path)
    })

df_hash = pd.DataFrame(hash_records)

if not df_hash.empty:

    duplicate_files = df_hash[
        df_hash.duplicated(subset="hash", keep=False)
    ].sort_values("hash")

    duplicate_groups = duplicate_files["hash"].nunique()

    print(f"Jumlah kelompok file identik: {duplicate_groups}")
    print(f"Jumlah file dalam kelompok duplikat: "
          f"{len(duplicate_files)}")

    if not duplicate_files.empty:
        print("\nDaftar file duplikat:")
        print(duplicate_files.to_string(index=False))
    else:
        print("Tidak ditemukan file PDF yang identik.")

    duplicate_files.to_csv(
        OUTPUT_DIR / "duplikasi_file.csv",
        index=False,
        encoding="utf-8-sig"
    )

# Pemeriksaan Metadata
print("\nPEMERIKSAAN METADATA")

df_metadata = pd.read_csv(METADATA_PATH, encoding="utf-8-sig")

print(f"Jumlah baris metadata : {len(df_metadata)}")
print(f"Jumlah kolom metadata : {len(df_metadata.columns)}")

print("\nNama kolom metadata:")

for column in df_metadata.columns:
    print(f"- {column}")

print("\nLima data pertama:")
print(df_metadata.head().to_string(index=False))

# Pemeriksaan nilai kosong pada metadata
print("\nPEMERIKSAAN NILAI KOSONG METADATA")

missing_data = pd.DataFrame({
    "kolom": df_metadata.columns,
    "jumlah_kosong": df_metadata.isnull().sum().values,
    "persentase_kosong": (
        df_metadata.isnull().mean().values * 100
    ).round(2)
})

print(missing_data.to_string(index=False))
missing_data.to_csv(OUTPUT_DIR / "nilai_kosong_metadata.csv", index=False, encoding="utf-8-sig")

# Pemeriksaan duplikasi metadata
print("\nPEMERIKSAAN DUPLIKASI METADATA")

duplicate_rows = df_metadata.duplicated().sum()

print(f"Jumlah baris duplikat: {duplicate_rows}")

# Memeriksa kolom yang berpotensi menjadi identitas artikel
possible_columns = [
    "filename",
    "file_name",
    "nama_file",
    "title",
    "judul",
    "doi",
    "url",
    "link"
]

for column in possible_columns:

    if column in df_metadata.columns:

        duplicate_count = df_metadata[column].duplicated(keep=False).sum()

        print(
            f"Duplikasi berdasarkan {column}: "
            f"{duplicate_count}"
        )

# Ringkasan hasil pemeriksaan dataset
print("\nRINGKASAN HASIL AUDIT")
print(f"Jumlah seluruh file       : {len(all_files)}")
print(f"Jumlah file PDF           : {len(pdf_files)}")
print(f"Jumlah file selain PDF    : {len(other_files)}")
print(f"Jumlah metadata           : {len(df_metadata)}")

if not df_files.empty:
    print(
        f"PDF kosong                : "
        f"{df_files['file_kosong'].sum()}"
    )

    print(
        f"PDF perlu diperiksa       : "
        f"{(df_files['indikasi_nama'] == 'Perlu diperiksa').sum()}"
    )

if not df_hash.empty:
    print(
        f"Kelompok PDF duplikat     : "
        f"{df_hash['hash'].duplicated(keep=False).sum()}"
    )

print(f"\nHasil disimpan di: {OUTPUT_DIR.resolve()}")
print("Pemeriksaan dataset selesai")