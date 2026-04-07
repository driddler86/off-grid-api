import streamlit as st
import json
from unified_scout import UnifiedScout

st.set_page_config(page_title="Off-Grid Property Scout", page_icon="🏕️", layout="wide")

st.title("🏕️ Autonomous Off-Grid Property Scout")
st.markdown("Enter the details of a land plot below to run the **Grand Unification Engine** (Discovery + Evaluation).")

with st.sidebar:
    st.header("📍 Plot Details")
    lat = st.number_input("Latitude", value=50.2660, format="%.6f")
    lon = st.number_input("Longitude", value=-5.0527, format="%.6f")

    st.header("📄 Listing Info")
    listing_url = st.text_input("Listing URL (Optional)")
    listing_text = st.text_area(
        "Listing Description",
        value="Beautiful off-grid amenity land. No services, completely unconnected. Spring water available."
    )

    st.header("📜 Policy Document")
    pdf_url = st.text_input(
        "Local Plan PDF URL",
        value="https://assets.publishing.service.gov.uk/media/65a11af7e8f5ec000f1f8c46/NPPF_December_2023.pdf"
    )

    run_button = st.button("🚀 Run Unified Scout", type="primary")

if run_button:
    # Input validation
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        st.error("❌ Invalid coordinates. Latitude must be between -90 and 90, longitude between -180 and 180.")
        st.stop()

    if not (-8.65 <= lon <= 1.77) or not (49.86 <= lat <= 60.86):
        st.warning("⚠️ Coordinates appear to be outside the UK. Results may be incomplete or inaccurate.")

    with st.spinner("Agents are scouting the location... This may take a minute."):
        try:
            scout = UnifiedScout()
            url_to_use = listing_url.strip() if listing_url.strip() else None
            text_to_use = listing_text if not url_to_use else None

            report = scout.run_full_scout(
                lat=lat,
                lon=lon,
                text_description=text_to_use,
                url=url_to_use,
                pdf_url=pdf_url if pdf_url.strip() else None
            )

        except Exception as e:
            st.error(f"❌ Scout encountered an unexpected error: {str(e)}")
            st.info("Try again in a moment, or check that all API services are reachable.")
            with st.expander("Technical details"):
                st.code(str(e))
            st.stop()

    if not report:
        st.error("❌ Scout returned no data. Please try again.")
        st.stop()

    st.header("📊 Scouting Report")

    # Phase 1 Results
    st.subheader("Phase 1: Discovery Engine")
    p1 = report.get("phase_1_discovery", {})
    verdict = p1.get("FINAL_VERDICT", "Unknown")

    if "NO-GO" in verdict:
        st.error(f"Verdict: {verdict}")
    elif "PRIME" in verdict or "STRONG" in verdict:
        st.success(f"Verdict: {verdict}")
    else:
        st.warning(f"Verdict: {verdict}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Listing Score", p1.get("1_LISTING_ANALYSIS", {}).get("score", "N/A"))
    col2.metric("Stress Score", p1.get("2_ENVIRONMENTAL_STRESS", {}).get("score", "N/A"))
    col3.metric("History Score", p1.get("3_PLANNING_HISTORY", {}).get("score", "N/A"))

    with st.expander("View Phase 1 Details"):
        st.json(p1)

    # Phase 2 Results
    status = report.get("status", "")

    if status == "ABORTED_AT_PHASE_1":
        st.warning("🛑 Phase 2 Evaluation was skipped — plot failed Phase 1 critical checks.")

    elif status == "ERROR_IN_PHASE_2":
        p2_err = report.get("phase_2_evaluation", {})
        st.error(f"⚠️ Phase 2 encountered an error: {p2_err.get('error', 'Unknown error')}")
        st.info("Phase 1 results above are still valid. Phase 2 may be retried by running the scout again.")

    elif status == "COMPLETED" and report.get("phase_2_evaluation"):
        st.subheader("Phase 2: Evaluation Engine (Sovereignty Score)")
        p2 = report["phase_2_evaluation"]

        final_score = p2.get("final_score", 0)
        st.metric("👑 Final Sovereignty Score", f"{final_score} / 100")

        if p2.get("para_84_boost_applied"):
            st.info("👻 Paragraph 84 Boost Applied — Ghost Application potential detected!")

        c1, c2, c3, c4 = st.columns(4)
        bd = p2.get("breakdown", {})
        c1.metric("Planning", bd.get("planning", "N/A"))
        c2.metric("Energy", bd.get("energy", "N/A"))
        c3.metric("Resources", bd.get("resources", "N/A"))

        raw_data = p2.get("raw_data", {})
        access_data = raw_data.get("access", {})
        has_access = access_data.get("has_access", False)
        c4.metric("Terrain Access", "✅ Yes" if has_access else "❌ No")

        with st.expander("View Phase 2 Details (Raw Data)"):
            st.json(raw_data)

    else:
        st.error("⚠️ Unexpected status returned from scout. Please try again.")
        with st.expander("Raw report"):
            st.json(report)
