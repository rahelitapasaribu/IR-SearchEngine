import fnmatch
import time
from retrieval import InformationRetrieval

ir = InformationRetrieval()

test_queries = [
    "sistem*",
    "*digital",
    "*didik*",
    "d?gital",
    "digital",
    "term_tidak_ada*"
]


# PENGUJIAN
print("\nWILDCARD SEARCH EVALUATION")

results = []


for query in test_queries:
    start_time = time.perf_counter()
    result = ir.search(query)
    elapsed = time.perf_counter() - start_time
    matched_terms = result["matched_terms"]
    
    # Normalisasi query
    normalized = ir.normalize_query(query)

    # Membuat hasil pembanding
    if len(normalized) != 1:
        expected_terms = []
    else:
        pattern = normalized[0]

        if "*" in pattern or "?" in pattern:
            expected_terms = sorted([
                term for term in ir.dictionary

                if fnmatch.fnmatchcase(term, pattern)
            ])

        else:
            expected_terms = [pattern] if pattern in ir.dictionary else []


    wildcard_validation = (matched_terms == expected_terms)

    vbe_validation = True

    for term in matched_terms:
        postings = ir.search_term(term)

        if not isinstance(postings, dict):
            vbe_validation = False
            break

        if any(
            not isinstance(tf, int) or tf <= 0
            for tf in postings.values()
        ):
            vbe_validation = False
            break


    # Menyimpan hasil
    results.append({
        "query": query,
        "matched_terms": matched_terms,
        "total_terms": len(matched_terms),
        "total_documents": result["total_documents"],
        "processing_time": elapsed,
        "wildcard_validation": wildcard_validation,
        "vbe_validation": vbe_validation

    })


    # Menampilkan hasil
    print("\n-----------------------------------")
    print("Query:", query)
    print("Matched terms:", matched_terms)
    print(
        "Total matched terms:",
        len(matched_terms)
    )
    print(
        "Total documents:",
        result["total_documents"]
    )
    print(
        "Processing time:",
        f"{elapsed:.8f} seconds"
    )
    print(
        "Wildcard validation:",
        "PASS" if wildcard_validation else "FAIL"
    )
    print(
        "VBE validation:",
        "PASS" if vbe_validation else "FAIL"
    )

    if not matched_terms:
        print("Status: No matching term found")


# RINGKASAN
print("\n===================================")
print("SUMMARY OF TESTING")
print("===================================")

total_tests = len(results)
passed_tests = sum(
    result["wildcard_validation"]
    and result["vbe_validation"]

    for result in results

)

failed_tests = total_tests - passed_tests

print("Total tests:", total_tests)
print("Passed:", passed_tests)
print("Failed:", failed_tests)


# WAKTU PEMROSESAN
print("\nPROCESSING TIME")

for result in results:
    print(
        f"{result['query']}: "
        f"{result['processing_time']:.8f} seconds"
    )


if total_tests > 0:
    average_time = sum(
        result["processing_time"]

        for result in results

    ) / total_tests

    print(
        "\nAverage processing time:",
        f"{average_time:.8f} seconds"
    )


# STATUS AKHIR
print("\n===================================")

if failed_tests == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
print("===================================")
