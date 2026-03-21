import requests
from bs4 import BeautifulSoup

class ListingHunter:
    def __init__(self):
        self.positive_keywords = [
            "unconnected", "spring water", "dilapidated barn", 
            "amenity land", "off-grid", "off grid", "no services",
            "pasture", "woodland", "nature reserve", "stream", "borehole",
            "agricultural land", "grazing"
        ]
        self.negative_keywords = [
            "development potential", "planning granted", "overage", 
            "uplift clause", "residential development", "houses", 
            "building plot", "investor", "lapsed planning", "10 houses"
        ]

    def analyze_text(self, text):
        text_lower = text.lower()
        pos_found = [kw for kw in self.positive_keywords if kw in text_lower]
        neg_found = [kw for kw in self.negative_keywords if kw in text_lower]

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
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text(separator=' ', strip=True)
            analysis = self.analyze_text(text)
            analysis['url'] = url
            return analysis
        except Exception as e:
            return {"error": str(e), "url": url}
