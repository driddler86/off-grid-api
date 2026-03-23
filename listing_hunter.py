import requests
import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger("off-grid-api")


class ListingHunter:
    def __init__(self):
        # --- Issue #8: Improved keywords with variations and regex patterns ---
        self.positive_patterns = [
            r"un\s*connected",        # unconnected, un connected
            r"spring\s*water",         # spring water, springwater
            r"dilapidated\s*barn",     # dilapidated barn
            r"amenity\s*land",         # amenity land
            r"off[\s\-]?grid",         # off-grid, off grid, offgrid
            r"no\s*services",          # no services
            r"pasture",
            r"woodland",
            r"nature\s*reserve",
            r"stream",
            r"borehole",
            r"agricultural\s*land",
            r"grazing",
            r"rural",
            r"isolated",
            r"barn\s*conversion",
            r"stone\s*barn",
            r"derelict",
            r"ruin",
            r"smallholding",
            r"homestead",
            r"well\s*water",
            r"solar",
            r"wind\s*turbine",
            r"septic\s*tank",
            r"class\s*q",              # Class Q permitted development
        ]
        self.negative_patterns = [
            r"development\s*potential",
            r"planning\s*(permission\s*)?granted",
            r"overage(\s*clause)?",
            r"uplift\s*clause",
            r"residential\s*development",
            r"\b\d+\s*houses\b",      # "10 houses", "5 houses" etc.
            r"building\s*plot",
            r"investor",
            r"lapsed\s*planning",
            r"strategic\s*land",
            r"land\s*bank",
            r"spec(ulative)?\s*build",
            r"developer",
        ]

    def analyze_text(self, text):
        text_lower = text.lower()

        pos_found = []
        for pattern in self.positive_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                pos_found.append(pattern.replace("\\s*", " ").replace("\\s+", " ").strip())

        neg_found = []
        for pattern in self.negative_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                neg_found.append(pattern.replace("\\s*", " ").replace("\\s+", " ").strip())

        score = len(pos_found) * 10
        is_rejected = len(neg_found) > 0
        if is_rejected:
            score -= len(neg_found) * 50

        return {
            "score": score,
            "positive_matches": pos_found,
            "negative_matches": neg_found,
            "is_viable": score > 0 and not is_rejected
        }

    def scrape_listing(self, url):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text(separator=" ", strip=True)
            analysis = self.analyze_text(text)
            analysis["url"] = url
            return analysis
        except Exception as e:
            logger.error(f"Failed to scrape listing {url}: {e}")
            return {"error": str(e), "url": url, "score": 0, "is_viable": True}
