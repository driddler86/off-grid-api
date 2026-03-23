import pytest
import json
from unittest.mock import patch, MagicMock

# ============================================================
# Test ListingHunter
# ============================================================

class TestListingHunter:
    def setup_method(self):
        from listing_hunter import ListingHunter
        self.hunter = ListingHunter()

    def test_positive_keywords_detected(self):
        text = "Beautiful off-grid amenity land with spring water and a dilapidated barn."
        result = self.hunter.analyze_text(text)
        assert result["score"] > 0
        assert result["is_viable"] is True
        assert len(result["positive_matches"]) > 0

    def test_negative_keywords_reject(self):
        text = "Development potential with planning granted for 10 houses. Investor opportunity."
        result = self.hunter.analyze_text(text)
        assert result["is_viable"] is False
        assert len(result["negative_matches"]) > 0

    def test_mixed_keywords(self):
        text = "Off-grid land with development potential."
        result = self.hunter.analyze_text(text)
        assert result["is_viable"] is False  # Negative overrides positive

    def test_empty_text(self):
        result = self.hunter.analyze_text("")
        assert result["score"] == 0
        assert result["is_viable"] is False  # score is not > 0

    def test_offgrid_variations(self):
        """Test that different spellings of off-grid are caught."""
        for variant in ["off-grid", "off grid", "offgrid"]:
            result = self.hunter.analyze_text(f"This is {variant} land")
            assert len(result["positive_matches"]) > 0, f"Failed to match: {variant}"


# ============================================================
# Test SovereigntyScorer
# ============================================================

class TestSovereigntyScorer:
    def setup_method(self):
        from scoring import SovereigntyScorer
        self.scorer = SovereigntyScorer()

    def test_normalize_energy_basic(self):
        data = {"solar_kwh_m2_day": 3.0, "wind_m_s": 5.0}
        score = self.scorer.normalize_energy(data)
        assert 0 <= score <= 1.0

    def test_normalize_energy_none(self):
        assert self.scorer.normalize_energy(None) == 0.0

    def test_normalize_energy_south_facing_boost(self):
        data = {"solar_kwh_m2_day": 3.0, "wind_m_s": 5.0}
        terrain_south = {"aspect_degrees": 180, "is_south_facing": True}
        terrain_north = {"aspect_degrees": 0, "is_south_facing": False}

        score_south = self.scorer.normalize_energy(data, terrain_south)
        score_north = self.scorer.normalize_energy(data, terrain_north)
        assert score_south > score_north

    def test_normalize_resource_high_aquifer(self):
        data = {"aquifer": {"productivity": "High productivity"}}
        score = self.scorer.normalize_resource(data)
        assert score > 0.5

    def test_normalize_resource_low_aquifer(self):
        data = {"aquifer": {"productivity": "Low productivity"}}
        score = self.scorer.normalize_resource(data)
        assert score < 0.5

    def test_normalize_resource_none(self):
        assert self.scorer.normalize_resource(None) == 0.0

    def test_sovereignty_score_range(self):
        score = self.scorer.calculate_sovereignty_score(0.8, 0.6, 0.5)
        assert 0 <= score <= 100

    def test_access_penalty(self):
        score_access = self.scorer.calculate_sovereignty_score(0.8, 0.6, 0.5, has_access=True)
        score_no_access = self.scorer.calculate_sovereignty_score(0.8, 0.6, 0.5, has_access=False)
        assert score_no_access == pytest.approx(score_access * 0.5, rel=0.01)


# ============================================================
# Test StressHunter (with mocked APIs)
# ============================================================

class TestStressHunter:
    def setup_method(self):
        from stress_hunter import StressHunter
        self.hunter = StressHunter()

    @patch("stress_hunter.requests.get")
    def test_flood_zone_3_detected(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"features": [{"attributes": {"zone": 3}}]}
        mock_get.return_value = mock_response

        result = self.hunter.check_flood_risk(51.5, -0.09)
        assert result["in_flood_zone_3"] is True
        assert result["score_modifier"] == -100

    @patch("stress_hunter.requests.get")
    def test_no_flood_risk(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"features": []}
        mock_get.return_value = mock_response

        result = self.hunter.check_flood_risk(57.1, -4.5)
        assert result["in_flood_zone_3"] is False
        assert result["score_modifier"] == 10

    @patch("stress_hunter.requests.post")
    def test_completely_off_grid(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"elements": []}
        mock_post.return_value = mock_response

        result = self.hunter.check_grid_distance(57.1, -4.5)
        assert result["status"] == "Completely Off-Grid (>2km)"
        assert result["score_modifier"] == 50


# ============================================================
# Test HistoryHunter (with mocked API)
# ============================================================

class TestHistoryHunter:
    def setup_method(self):
        from history_hunter import HistoryHunter
        self.hunter = HistoryHunter()

    @patch("history_hunter.requests.get")
    def test_ghost_application_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": [
                {
                    "uid": "APP/001",
                    "description": "Erection of a new dwelling house",
                    "decided": "Refused",
                    "start_date": "2022-01-01",
                    "url": "http://example.com/app/001"
                }
            ]
        }
        mock_get.return_value = mock_response

        result = self.hunter.search_ghost_applications(50.26, -5.05)
        assert result["is_para84_candidate"] is True
        assert result["ghost_applications_found"] == 1
        assert result["score_modifier"] == 100

    @patch("history_hunter.requests.get")
    def test_no_ghost_applications(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"records": []}
        mock_get.return_value = mock_response

        result = self.hunter.search_ghost_applications(50.26, -5.05)
        assert result["is_para84_candidate"] is False
        assert result["score_modifier"] == 0


# ============================================================
# Test Cache
# ============================================================

class TestCache:
    def setup_method(self):
        from cache import SimpleCache
        self.cache = SimpleCache(ttl=10, max_size=3)

    def test_set_and_get(self):
        self.cache.set("key1", {"data": "test"})
        result = self.cache.get("key1")
        assert result == {"data": "test"}

    def test_missing_key(self):
        assert self.cache.get("nonexistent") is None

    def test_max_size_eviction(self):
        self.cache.set("k1", 1)
        self.cache.set("k2", 2)
        self.cache.set("k3", 3)
        self.cache.set("k4", 4)  # Should evict k1
        assert self.cache.get("k1") is None
        assert self.cache.get("k4") == 4
        assert self.cache.size == 3

    def test_clear(self):
        self.cache.set("k1", 1)
        self.cache.set("k2", 2)
        self.cache.clear()
        assert self.cache.size == 0


# ============================================================
# Test PolicyHunter
# ============================================================

class TestPolicyHunter:
    def setup_method(self):
        from policy_hunter import PolicyHunter
        self.hunter = PolicyHunter()

    def test_score_with_keywords(self):
        text = "class q development is allowed under paragraph 84 for sustainable development on brownfield sites"
        score, findings = self.hunter.score_document(text)
        assert score > 0
        assert findings["class q"] > 0
        assert findings["paragraph 84"] > 0

    def test_score_no_keywords(self):
        text = "the quick brown fox jumps over the lazy dog"
        score, findings = self.hunter.score_document(text)
        assert score == 0

    def test_score_capped_at_one(self):
        text = "class q " * 100 + "paragraph 84 " * 100 + "brownfield " * 100
        score, _ = self.hunter.score_document(text)
        assert score <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
