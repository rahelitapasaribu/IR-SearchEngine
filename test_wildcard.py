import fnmatch
import time
from retrieval import InformationRetrieval

ir = InformationRetrieval()

# Pola pengujian
test_queries = [
    "sistem*",
    "*digital",
    "*didik*",
    "digital",
    "term_tidak_ada*"
]

print("\nWILDCARD SEARCH EVALUATION")

results = []

for query in test_queries:

    # Mengukur waktu pemrosesan
    start_time = time.perf_counter()

    result = ir.search(query)

    elapsed = time.perf_counter() - start_time

    matched_terms = result["matched_terms"]

    # Validasi kecocokan pola
    if "*" in query or "?" in query:

        validation = all(
            fnmatch.fnmatchcase(term, query)
            for term in matched_terms
        )

    else:

        validation = all(
            term == query
            for term in matched_terms
        )

    # Menyimpan hasil pengujian
    results.append({
        "query": query,
        "matched_terms": matched_terms,
        "total_terms": len(matched_terms),
        "total_documents": result["total_documents"],
        "processing_time": elapsed,
        "validation": validation
    })

    print("\nQuery:", query)
    print("Matched terms:", matched_terms)
    print("Total matched terms:", len(matched_terms))
    print("Total documents:", result["total_documents"])
    print(f"Processing time: {elapsed:.8f} seconds")
    print("Validation:", "PASS" if validation else "FAIL")

    if not matched_terms:
        print("Status: No matching term found")


# Ringkasan pengujian
print("\nSUMMARY OF TESTING")

total_tests = len(results)

passed_tests = sum(
    result["validation"]
    for result in results
)

failed_tests = total_tests - passed_tests

print("Total tests:", total_tests)
print("Passed:", passed_tests)
print("Failed:", failed_tests)

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
        f"\nAverage processing time: "
        f"{average_time:.8f} seconds"
    )
