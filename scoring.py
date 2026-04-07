import logging

logger = logging.getLogger("off-grid-api.scoring")


class SovereigntyScorer:
    """Consolidated scoring engine for the Off-Grid Scout system."""

    def __init__(self):
        self.weight_planning = 0.40
        self.weight_energy = 0.30
        self.weight_resources = 0.30

    def normalize_energy(self, energy_data, terrain_data=None):
        """Normalize energy data into a 0-1 score with terrain modifiers."""
        if not energy_data:
            return 0.0
        solar = energy_data.get("solar_kwh_m2_day", 0)
        wind = energy_data.get("wind_m_s", 0)

        # Apply terrain modifiers to raw solar value BEFORE normalizing,
        # so the boost/penalty is not cancelled out by the 1.0 cap.
        if terrain_data:
            aspect = terrain_data.get("aspect_degrees")
            is_south = terrain_data.get("is_south_facing", False)
            if is_south:
                solar = solar * 1.1  # 10% boost for south-facing
                logger.info(f"South-facing boost applied: solar adjusted to {solar:.3f} kWh/m²/day")
            elif aspect is not None and (aspect > 315 or aspect < 45):  # North-facing
                solar = solar * 0.7  # 30% penalty
                logger.info(f"North-facing penalty applied: solar adjusted to {solar:.3f} kWh/m²/day")

        solar_score = min(solar / 4.0, 1.0)
        wind_score = min(wind / 10.0, 1.0)

        return round((solar_score + wind_score) / 2.0, 4)

    def normalize_resource(self, resource_data):
        """Normalize resource data into a 0-1 score using actual soil and aquifer data."""
        if not resource_data:
            return 0.0

        # Aquifer score
        aquifer_prod = resource_data.get("aquifer", {}).get("productivity", "").lower()
        if "high" in aquifer_prod:
            aq_score = 1.0
        elif "moderate" in aquifer_prod:
            aq_score = 0.7
        elif "low" in aquifer_prod:
            aq_score = 0.4
        else:
            aq_score = 0.2

        # Soil score — use actual texture data from resource_hunter (BGS/UKSO)
        soil_texture = resource_data.get("soil", {}).get("texture", "").lower()
        soil_desc = resource_data.get("soil", {}).get("soil_description", "").lower()

        if any(t in soil_texture for t in ["loam", "sandy loam", "clay loam", "silt loam"]):
            soil_score = 0.8   # Highly productive for growing
        elif any(t in soil_texture for t in ["sand", "sandy"]):
            soil_score = 0.65  # Good drainage, moderate fertility
        elif any(t in soil_texture for t in ["silty", "silt"]):
            soil_score = 0.60  # Moderate
        elif any(t in soil_texture for t in ["clay"]):
            soil_score = 0.45  # Poor drainage, harder to work
        elif any(t in soil_texture for t in ["peat", "organic", "bog"]):
            soil_score = 0.30  # Acidic, poor structural support
        elif soil_texture or soil_desc:
            soil_score = 0.55  # Data present but unrecognised texture
        else:
            soil_score = 0.50  # No data — neutral fallback

        logger.info(f"Resource scores — aquifer: {aq_score}, soil: {soil_score} (texture: '{soil_texture or 'unknown'}')")
        return round((aq_score + soil_score) / 2.0, 4)

    def calculate_planning_score(self, class_q_prob, para_84_prob, brownfield_prob):
        """Calculate planning score from individual probabilities."""
        return max(class_q_prob, para_84_prob, brownfield_prob)

    def calculate_sovereignty_score(self, p_score, e_score, r_score, has_access=True):
        """Calculate the final Sovereignty Score (0-100)."""
        base = (
            (p_score * self.weight_planning)
            + (e_score * self.weight_energy)
            + (r_score * self.weight_resources)
        )

        # Access modifier (critical)
        if not has_access:
            base *= 0.5  # 50% penalty for no road access
            logger.info("Applied 50% access penalty — no road access")

        final = round(base * 100, 2)
        logger.info(
            f"Sovereignty Score: {final}/100 "
            f"(P={p_score}, E={e_score}, R={r_score}, Access={has_access})"
        )
        return final


# Example usage
if __name__ == "__main__":
    scorer = SovereigntyScorer()

    e = scorer.normalize_energy(
        {"solar_kwh_m2_day": 3.5, "wind_m_s": 6.0},
        {"is_south_facing": True, "aspect_degrees": 180}
    )
    r = scorer.normalize_resource({
        "aquifer": {"productivity": "Moderate"},
        "soil": {"texture": "Sandy loam", "soil_description": "Well-drained sandy loam"}
    })
    p = 0.8  # From policy_hunter

    score = scorer.calculate_sovereignty_score(p, e, r, has_access=True)
    print(f"Planning Score: {p}")
    print(f"Energy Score:   {e}")
    print(f"Resource Score: {r}")
    print(f"Sovereignty Score: {score}/100")

