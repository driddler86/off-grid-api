import os
import requests
import pypdf
import re
import logging
logger = logging.getLogger("off-grid-api.policy_hunter")


class PolicyHunter:
    def __init__(self):
        # Keywords and their base weights for the Planning Score (P)
        self.keywords = {
            "class q": 0.4,
            "paragraph 84": 0.4,
            "brownfield": 0.3,
            "sustainable development": 0.2,
            "renewable energy": 0.2,
            "isolated dwellings": 0.3
        }

    def download_pdf(self, url: str, save_path: str) -> str:
        logger.info(f"Downloading document from {url}...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return save_path

    def extract_text(self, pdf_path: str) -> str:
        logger.info(f"Extracting text from {pdf_path}...")
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = pypdf.PdfReader(file)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + " "
        return text.lower()

    def score_document(self, text: str) -> tuple:
        logger.info("Scoring document based on keywords...")
        score = 0.0
        findings = {}

        for keyword, weight in self.keywords.items():
            # Find exact matches of the keyword
            count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text))
            findings[keyword] = count

            if count > 0:
                # Base weight + small bonus for multiple mentions (capped at 5)
                score += weight + (min(count, 5) * 0.02)

        # Normalize score to a maximum of 1.0
        normalized_score = min(round(score, 4), 1.0)
        return normalized_score, findings

if __name__ == '__main__':
    hunter = PolicyHunter()

    # Test with the actual UK National Planning Policy Framework (NPPF) PDF
    nppf_url = "https://assets.publishing.service.gov.uk/media/65a11af7e8f5ec000f1f8c46/NPPF_December_2023.pdf"
    pdf_path = "/root/off-grid-property-scout/nppf_sample.pdf"

    try:
        hunter.download_pdf(nppf_url, pdf_path)
        doc_text = hunter.extract_text(pdf_path)
        final_score, keyword_counts = hunter.score_document(doc_text)

        print("\n--- Policy Hunter Results ---")
        print(f"Document Length: {len(doc_text)} characters")
        print("Keyword Mentions:")
        for kw, count in keyword_counts.items():
            print(f"  - '{kw.title()}': {count} times")
        print(f"\nCalculated Planning Score (P): {final_score} / 1.0")

    except Exception as e:
        print(f"Error during execution: {e}")
