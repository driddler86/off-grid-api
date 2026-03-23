import argparse
import json
import tempfile
import os
import logging
from scoring import SovereigntyScorer
from policy_hunter import PolicyHunter
from energy_hunter import EnergyHunter
from resource_hunter import ResourceHunter
from os_land_rover import OSLandRover

logger = logging.getLogger("off-grid-api.master_scout")


def evaluate_location(lat, lon, pdf_url):
    """Run Phase 2 deep evaluation on a location."""
    scorer = SovereigntyScorer()

    # 1. Terrain & Access
    rover = OSLandRover()
    land_data = rover.scout_location(lat, lon)
    terrain = land_data["terrain"]
    access = land_data["access"]

    # 2. Energy
    e_hunter = EnergyHunter()
    e_data = e_hunter.get_energy_score_data(lat, lon)
    e_score = scorer.normalize_energy(e_data, terrain)

    # 3. Resource
    r_hunter = ResourceHunter()
    r_data = r_hunter.get_resource_score_data(lat, lon)
    r_score = scorer.normalize_resource(r_data)

    # 4. Planning (with temp file cleanup)
    p_hunter = PolicyHunter()
    tmp_fd, pdf_path = tempfile.mkstemp(suffix=".pdf", prefix="off_grid_plan_")
    os.close(tmp_fd)

    try:
        p_hunter.download_pdf(pdf_url, pdf_path)
        doc_text = p_hunter.extract_text(pdf_path)
        p_score, findings = p_hunter.score_document(doc_text)
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            logger.info(f"Cleaned up temp PDF: {pdf_path}")

    # Calculate final Sovereignty Score using consolidated scorer
    has_access = access.get("has_access", False)
    final_score = scorer.calculate_sovereignty_score(p_score, e_score, r_score, has_access)

    return {
        "final_score": final_score,
        "breakdown": {
            "planning": p_score,
            "energy": e_score,
            "resources": r_score
        },
        "raw_data": {
            "terrain": terrain,
            "access": access,
            "energy": e_data,
            "resources": r_data,
            "planning_findings": findings
        }
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--pdf", type=str, default="https://assets.publishing.service.gov.uk/media/65a11af7e8f5ec000f1f8c46/NPPF_December_2023.pdf")
    args = parser.parse_args()

    result = evaluate_location(args.lat, args.lon, args.pdf)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
