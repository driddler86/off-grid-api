import streamlit as st
import json
from unified_scout import UnifiedScout

st.set_page_config(page_title="Off-Grid Property Scout", page_icon="\U0001F3D5\uFE0F", layout="wide")

st.title("\U0001F3D5\uFE0F Autonomous Off-Grid Property Scout")
st.markdown("Enter the details of a land plot below to run the **Grand Unification Engine** (Discovery + Evaluation).")

with st.sidebar:
    st.header("\U0001F4CD Plot Details")
    lat = st.number_input("Latitude", value=50.2660, format="%.6f")
    lon = st.number_input("Longitude", value=-5.0527, format="%.6f")
    
    st.header("\U0001F4C4 Listing Info")
    listing_url = st.text_input("Listing URL (Optional)")
    listing_text = st.text_area("Listing Description", value="Beautiful off-grid amenity land. No services, completely unconnected. Spring water available.")
    
    st.header("\U0001F4DC Policy Document")
    pdf_url = st.text_input("Local Plan PDF URL", value="https://assets.publishing.service.gov.uk/media/65a11af7e8f5ec000f1f8c46/NPPF_December_2023.pdf")
    
    run_button = st.button("\U0001F680 Run Unified Scout", type="primary")

if run_button:
    with st.spinner("Agents are scouting the location... This may take a minute."):
        scout = UnifiedScout()
        url_to_use = listing_url if listing_url.strip() else None
        text_to_use = listing_text if not url_to_use else None
        
        report = scout.run_full_scout(
            lat=lat, 
            lon=lon, 
            text_description=text_to_use, 
            url=url_to_use, 
            pdf_url=pdf_url
        )
        
        st.header("\U0001F4CA Scouting Report")
        
        # Phase 1 Results
        st.subheader("Phase 1: Discovery Engine")
        p1 = report.get("phase_1_discovery", {})
        verdict = p1.get("FINAL_VERDICT", "Unknown")
        
        if "NO-GO" in verdict:
            st.error(f"Verdict: {verdict}")
        elif "PRIME" in verdict:
            st.success(f"Verdict: {verdict}")
        elif "STRONG" in verdict:
            st.success(f"Verdict: {verdict}")
        else:
            st.warning(f"Verdict: {verdict}")
            
        col1, col2, col3 = st.columns(3)
        col1.metric("Listing Score", p1.get("1_LISTING_ANALYSIS", {}).get("score", 0))
        col2.metric("Stress Score", p1.get("2_ENVIRONMENTAL_STRESS", {}).get("score", 0))
        col3.metric("History Score", p1.get("3_PLANNING_HISTORY", {}).get("score", 0))
        
        with st.expander("View Phase 1 Details"):
            st.json(p1)
            
        # Phase 2 Results
        if report.get("status") == "COMPLETED" and report.get("phase_2_evaluation"):
            st.subheader("Phase 2: Evaluation Engine (Sovereignty Score)")
            p2 = report["phase_2_evaluation"]
            
            st.metric("\U0001F451 Final Sovereignty Score", f"{p2.get('final_score', 0)} / 100")
            
            if p2.get("para_84_boost_applied"):
                st.info("\U0001F47B Paragraph 84 Boost Applied due to Ghost Application!")
                
            c1, c2, c3, c4 = st.columns(4)
            bd = p2.get("breakdown", {})
            c1.metric("Planning", bd.get("planning", 0))
            c2.metric("Energy", bd.get("energy", 0))
            c3.metric("Resources", bd.get("resources", 0))
            
            # Safely get access data
            raw_data = p2.get("raw_data", {})
            access_data = raw_data.get("access", {})
            has_access = access_data.get("has_access", False)
            c4.metric("Terrain Access", "Yes" if has_access else "No")
            
            with st.expander("View Phase 2 Details (Raw Data)"):
                st.json(raw_data)
        elif report.get("status") == "ABORTED_AT_PHASE_1":
            st.warning("\U0001F6D1 Phase 2 Evaluation was aborted because the plot failed Phase 1 critical checks.")
        else:
            st.error("\u26A0\uFE0F Phase 2 Evaluation encountered an error.")
