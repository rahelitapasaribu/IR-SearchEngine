import json
import time
from pathlib import Path

INDEX_DIR = Path("index")

INVERTED_INDEX_PATH = INDEX_DIR / "inverted_index.json"
DICTIONARY_PATH = INDEX_DIR / "dictionary.json"

VBE_DATA_PATH = INDEX_DIR / "postings_vbe.bin"
VBE_INDEX_PATH = INDEX_DIR / "vbe_index.json"
STATISTICS_PATH = INDEX_DIR / "vbe_statistics.json"

if not INVERTED_INDEX_PATH.exists():
    raise FileNotFoundError(f"Inverted index tidak ditemukan: {INVERTED_INDEX_PATH}")

if not DICTIONARY_PATH.exists():
    raise FileNotFoundError(f"Dictionary tidak ditemukan: {DICTIONARY_PATH}")

# Load inverted index
print("VARIABLE BYTE ENCODING")

with open(INVERTED_INDEX_PATH, "r", encoding="utf-8") as file:
    inverted_index = json.load(file)

with open(DICTIONARY_PATH, "r", encoding="utf-8") as file:
    dictionary = json.load(file)


print("Inverted index berhasil dimuat")
print("Dictionary berhasil dimuat")
print("Jumlah term:", len(inverted_index))

# Fungsi Variable Byte Encoding (VBE) dan Gap Encoding
def vb_encode_number(number):
    """
    Mengubah satu integer menjadi Variable Byte Encoding.

    Bit MSB:
    - 1 = masih ada byte lanjutan
    - 0 = byte terakhir
    """

    if not isinstance(number, int) or number < 0:
        raise ValueError("VBE hanya menerima integer non-negatif")

    # Mengambil 7 bit paling rendah
    encoded = [number % 128]

    number //= 128

    # Mengambil kelompok 7 bit berikutnya
    while number > 0:

        encoded.append(number % 128)

        number //= 128

    # Mengurutkan dari kelompok paling signifikan
    encoded.reverse()

    # Memberikan continuation bit
    for i in range(len(encoded) - 1):
        encoded[i] |= 128

    return bytes(encoded)


def vb_encode(numbers):
    """
    Mengompresi sekumpulan integer menggunakan VBE.
    """

    result = bytearray()

    for number in numbers:

        result.extend(vb_encode_number(number))

    return bytes(result)

# Fungsi Variable Byte Decoding (VBD) dan Gap Decoding
def vb_decode(data):
    """
    Mengembalikan byte VBE menjadi sekumpulan integer.
    """

    numbers = []
    number = 0

    for byte in data:

        # Mengambil 7 bit informasi
        number = (number << 7) | (byte & 127)

        # MSB 0 berarti integer selesai
        if byte < 128:

            numbers.append(number)

            number = 0

    if number != 0:
        raise ValueError("Data VBE tidak lengkap atau rusak")

    return numbers

# Fungsi Gap Encoding dan Decoding
def gap_encode(doc_ids):
    """
    Mengubah docID terurut menjadi selisih antar-ID.
    """

    gaps = []

    previous_id = 0

    for doc_id in doc_ids:

        gap = doc_id - previous_id

        if gap < 0:
            raise ValueError("DocID harus diurutkan secara menaik")

        gaps.append(gap)

        previous_id = doc_id

    return gaps


def gap_decode(gaps):
    """
    Mengembalikan gap menjadi docID asli.
    """

    doc_ids = []

    previous_id = 0

    for gap in gaps:

        doc_id = previous_id + gap

        doc_ids.append(doc_id)

        previous_id = doc_id

    return doc_ids

# Fungsi Encoding dan Decoding Posting List
def encode_postings(postings):
    """
    Mengompresi posting list.

    Format integer yang dikompresi:
    [gap_docID, TF, gap_docID, TF, ...]

    Contoh:
    DocID = [1, 2, 5, 8]
    TF    = [5, 3, 2, 4]

    Integer:
    [1, 5, 1, 3, 3, 2, 3, 4]
    """

    # Mengurutkan docID secara numerik
    sorted_postings = sorted(postings.items(), key=lambda item: int(item[0]))

    doc_ids = []
    frequencies = []

    for doc_id, frequency in sorted_postings:

        numeric_id = int(doc_id)
        numeric_frequency = int(frequency)

        if numeric_id < 0:
            raise ValueError("DocID tidak boleh negatif")

        if numeric_frequency <= 0:
            raise ValueError("TF harus lebih besar dari 0")

        doc_ids.append(numeric_id)
        frequencies.append(numeric_frequency)

    # Gap Encoding
    gaps = gap_encode(doc_ids)

    # Menggabungkan gap dan TF secara bergantian
    numbers = []

    for gap, frequency in zip(gaps, frequencies):

        numbers.append(gap)
        numbers.append(frequency)

    # Variable Byte Encoding
    encoded_data = vb_encode(numbers)

    return encoded_data

# Fungsi Decoding Posting List
def decode_postings(encoded_data):
    """
    Mengembalikan data VBE menjadi posting list asli.
    """

    numbers = vb_decode(encoded_data)

    if len(numbers) % 2 != 0:
        raise ValueError("Jumlah integer hasil decoding tidak valid")

    gaps = numbers[0::2]
    frequencies = numbers[1::2]

    # Mengembalikan docID asli
    doc_ids = gap_decode(gaps)

    # Menggabungkan kembali docID dan TF
    postings = {
        str(doc_id): frequency
        for doc_id, frequency in zip(
            doc_ids,
            frequencies
        )
    }

    return postings

# Membangun VBE Index dan Menyimpan ke File
print("\nMemulai proses kompresi posting list")

start_time = time.perf_counter()

vbe_index = {}

total_postings = 0

with open(VBE_DATA_PATH, "wb") as binary_file:

    for term, postings in sorted(inverted_index.items()):

        # Posisi awal posting list
        offset = binary_file.tell()

        # Encoding posting list
        encoded_data = encode_postings(postings)

        # Menulis data ke file biner
        binary_file.write(encoded_data)

        # Hanya menyimpan offset dan byte length
        vbe_index[term] = [offset, len(encoded_data)]

        total_postings += len(postings)


encoding_time = time.perf_counter() - start_time

# Menyimpan VBE Index ke file JSON
with open(VBE_INDEX_PATH, "w", encoding="utf-8") as file:

    json.dump(vbe_index,file, separators=(",", ":"), ensure_ascii=False)

# Menghitung ukuran file dan rasio kompresi
original_size = INVERTED_INDEX_PATH.stat().st_size

compressed_data_size = VBE_DATA_PATH.stat().st_size

compressed_index_size = VBE_INDEX_PATH.stat().st_size

total_compressed_size = (compressed_data_size + compressed_index_size)

compression_ratio = (
    total_compressed_size / original_size * 100
    if original_size > 0 else 0
)

space_saving = (
    (original_size - total_compressed_size)
    / original_size * 100
    if original_size > 0 else 0
)

statistics = {
    "total_terms": len(inverted_index),
    "total_postings": total_postings,
    "original_index_size_bytes": original_size,
    "compressed_postings_size_bytes": (compressed_data_size),
    "vbe_index_size_bytes": compressed_index_size,
    "total_compressed_size_bytes": (total_compressed_size),
    "compression_ratio_percent": round(compression_ratio, 2),
    "space_saving_percent": round(space_saving, 2),
    "encoding_time_seconds": round(encoding_time, 6)
}

with open(STATISTICS_PATH, "w", encoding="utf-8") as file:

    json.dump(statistics, file, indent=4)

# Validasi Encoding dan Decoding
print("\nMelakukan validasi encoding dan decoding")

validation_success = True

with open(VBE_DATA_PATH, "rb") as binary_file:

    for term, information in vbe_index.items():

        offset, byte_length = information

        binary_file.seek(offset)

        encoded_data = binary_file.read(byte_length)

        decoded_postings = decode_postings(encoded_data)

        original_postings = {
            str(doc_id): int(frequency)
            for doc_id, frequency in inverted_index[term].items()
        }

        if decoded_postings != original_postings:
            validation_success = False
            print(f"Validasi gagal pada term: {term}")
            break

# Pengujian pencarian term dalam VBE Index
def search_vbe(term):

    term = term.lower().strip()

    if term not in vbe_index:
        return None

    # Mengambil offset dan panjang byte
    offset, byte_length = vbe_index[term]

    # Membaca informasi frekuensi dari dictionary
    information = dictionary[term]

    # Membaca data biner
    with open(VBE_DATA_PATH, "rb") as binary_file:

        binary_file.seek(offset)

        encoded_data = binary_file.read(byte_length)

    # Dekompresi
    postings = decode_postings(encoded_data)

    return {
        "term": term,
        "information": information,
        "postings": postings
    }

# Menampilkan hasil pengujian pencarian term
print("\nPENGUJIAN PENCARIAN POSTING LIST VBE")

test_terms = [
    "teknologi",
    "digital",
    "informasi",
    "aplikasi",
    "term_tidak_ada"
]

for term in test_terms:

    search_start = time.perf_counter()

    result = search_vbe(term)

    search_time = time.perf_counter() - search_start

    if result is not None:
        print(f"Term ditemukan: {term}")
        print("Document Frequency:", result["information"]["document_frequency"])
        print("Collection Frequency:", result["information"]["collection_frequency"])
        print("Jumlah posting:", len(result["postings"]))
        print("Contoh posting:", list(result["postings"].items())[:5])
    else:
        print(f"\nTerm tidak ditemukan: {term}")
    print(f"Waktu pencarian: {search_time:.8f} detik")

# Ringkasan hasil Variable Byte Encoding
print("\nVARIABLE BYTE ENCODING SELESAI")
print("Validasi encoding-decoding:", validation_success)

for key, value in statistics.items():

    print(f"{key}: {value}")

print("\nFile hasil:")
print("-", VBE_DATA_PATH)
print("-", VBE_INDEX_PATH)
print("-", STATISTICS_PATH)
