import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
import os
import time
import re

BASE_URL = "https://ejournal1.unud.ac.id"
ARCHIVE_URL = "https://ejournal1.unud.ac.id/index.php/jupita/issue/archive"
DATASET_FOLDER = "dataset"

os.makedirs(DATASET_FOLDER, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0"
}

session = requests.Session()
session.headers.update(headers)

# Get archive page
response = session.get(ARCHIVE_URL)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

issue_links = []

# Find all issues
for a in soup.find_all("a", href=True):
    href = a["href"]

    if "/index.php/jupita/issue/view/" in href:
        issue_url = urljoin(BASE_URL, href)

        if issue_url not in issue_links:
            issue_links.append(issue_url)

print("Total issues found:", len(issue_links))

metadata = []
document_id = 1

# Process each issue
for issue_index, issue_url in enumerate(issue_links, start=1):

    print(f"\nIssue {issue_index}/{len(issue_links)}")

    response = session.get(issue_url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Get issue information
    issue_title_tag = soup.select_one("h1")

    issue_title = (
        issue_title_tag.get_text(" ", strip=True)
        if issue_title_tag else ""
    )

    year_match = re.search(
        r"\b(20\d{2})\b",
        issue_title
    )

    year = (
        year_match.group(1)
        if year_match else "unknown"
    )

    volume_match = re.search(
        r"(?:Vol\.?|Volume)\s*(\d+)",
        issue_title,
        re.IGNORECASE
    )

    volume = (
        volume_match.group(1)
        if volume_match else ""
    )

    number_match = re.search(
        r"(?:No\.?|Nomor)\s*(\d+)",
        issue_title,
        re.IGNORECASE
    )

    issue_number = (
        number_match.group(1)
        if number_match else ""
    )

    print("Year:", year)
    print("Volume:", volume)
    print("Issue:", issue_number)

    articles = soup.select(
        "div.obj_article_summary"
    )

    print("Articles found:", len(articles))

    # Process each article
    for article in articles:

        title_tag = article.select_one(
            ".title a"
        )

        if not title_tag:
            continue

        title = title_tag.get_text(
            " ",
            strip=True
        )

        article_url = urljoin(
            BASE_URL,
            title_tag["href"]
        )

        author_tag = article.select_one(
            ".authors"
        )

        authors = (
            author_tag.get_text(" ", strip=True)
            if author_tag else ""
        )

        page_tag = article.select_one(
            ".pages"
        )

        pages = (
            page_tag.get_text(" ", strip=True)
            if page_tag else ""
        )

        pdf_tag = None

        # Find PDF link
        for a in article.find_all(
            "a",
            href=True
        ):

            if "PDF" in a.get_text(
                " ",
                strip=True
            ).upper():

                pdf_tag = a
                break

        if not pdf_tag:
            print("PDF not found:", title)
            continue

        view_url = urljoin(
            BASE_URL,
            pdf_tag["href"]
        )

        pdf_url = view_url.replace(
            "/article/view/",
            "/article/download/"
        )

        filename = (
            f"jupita_{year}_{document_id:04d}.pdf"
        )

        filepath = os.path.join(
            DATASET_FOLDER,
            filename
        )

        status = "Failed"

        # Download PDF
        try:
            pdf_response = session.get(
                pdf_url,
                timeout=60
            )

            if pdf_response.content.startswith(
                b"%PDF"
            ):

                with open(filepath, "wb") as f:
                    f.write(pdf_response.content)

                status = "Success"

                print(
                    f"[{document_id}] "
                    f"Downloaded: {filename}"
                )

            else:
                print(
                    f"[{document_id}] "
                    f"Not a PDF: {title}"
                )

        except Exception as e:
            print(
                f"[{document_id}] "
                f"Error: {e}"
            )

        # Save metadata
        metadata.append({
            "id": document_id,
            "title": title,
            "authors": authors,
            "year": year,
            "volume": volume,
            "issue": issue_number,
            "pages": pages,
            "article_url": article_url,
            "pdf_url": pdf_url,
            "filename": filename,
            "status": status
        })

        document_id += 1

        time.sleep(1)

# Save metadata
df = pd.DataFrame(metadata)

metadata_path = os.path.join(
    DATASET_FOLDER,
    "metadata.csv"
)

df.to_csv(
    metadata_path,
    index=False,
    encoding="utf-8-sig"
)

print("\nScraping completed")
print("Total issues:", len(issue_links))
print("Total documents:", len(df))
print(
    "Successful:",
    (df["status"] == "Success").sum()
)
print(
    "Failed:",
    (df["status"] == "Failed").sum()
)