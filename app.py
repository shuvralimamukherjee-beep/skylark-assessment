
import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import pandas as pd

st.set_page_config(page_title="Kolkata Healthcare Access", layout="wide")
st.title("Kolkata Healthcare Access Analysis")
st.caption("Skylark Drones GIS Assessment | Shuvra | 2026")

@st.cache_data
def load_data():
    facilities = gpd.read_file("outputs/facilities.gpkg").to_crs("EPSG:4326")
    isochrones = gpd.read_file("outputs/isochrones_with_load.gpkg").to_crs("EPSG:4326")
    unserved = gpd.read_file("outputs/unserved_area.gpkg").to_crs("EPSG:4326")
    proposed = gpd.read_file("outputs/proposed_facilities.gpkg").to_crs("EPSG:4326")
    return facilities, isochrones, unserved, proposed

facilities, isochrones, unserved, proposed = load_data()

tab1, tab2, tab3 = st.tabs(["Access Map", "Demand & Supply", "Proposed Facilities"])

with tab1:
    st.subheader("15-Minute Healthcare Access Zones")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Facilities", "253")
    col2.metric("Population Served", "968,057")
    col3.metric("Coverage", "19.8%")
    col4.metric("Unserved Population", "3,910,393")
    
    st.sidebar.header("Map Layers")
    show_iso = st.sidebar.checkbox("Show Access Zones", value=True)
    show_unserved = st.sidebar.checkbox("Show Unserved Areas", value=True)
    show_proposed = st.sidebar.checkbox("Show Proposed Facilities", value=True)
    show_load = st.sidebar.checkbox("Colour by Load Status", value=False)
    
    m = folium.Map(location=[22.5726, 88.3639], zoom_start=11, tiles="CartoDB positron")
    
    if show_unserved:
        folium.GeoJson(
            unserved.__geo_interface__,
            style_function=lambda x: {
                "fillColor": "#d62728",
                "color": "#d62728",
                "fillOpacity": 0.25,
                "weight": 0
            },
            tooltip="Unserved Area — no facility within 15 min"
        ).add_to(m)
    
    if show_iso:
        load_colors = {"Overloaded": "#e377c2", "Normal": "#2ca02c", "Underutilized": "#aec7e8"}
        for _, row in isochrones.iterrows():
            if row.geometry is None:
                continue
            color = load_colors.get(row.get("load_status", "Normal"), "#1f77b4") if show_load else "#1f77b4"
            folium.GeoJson(
                row.geometry.__geo_interface__,
                style_function=lambda x, c=color: {
                    "fillColor": c,
                    "color": c,
                    "fillOpacity": 0.15,
                    "weight": 0.5
                }
            ).add_to(m)
    
    for _, row in facilities.iterrows():
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=4,
            color="#1f77b4",
            fill=True,
            fill_opacity=0.8,
            popup=str(row.get("name", "Unnamed Facility"))
        ).add_to(m)
    
    if show_proposed:
        for i, row in proposed.iterrows():
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=12,
                color="#ff7f0e",
                fill=True,
                fill_color="#ff7f0e",
                fill_opacity=0.9,
                popup=f"PROPOSED Facility {i+1}<br>Population newly served: {row['pop_gain']:,.0f}"
            ).add_to(m)
    
    folium.LayerControl().add_to(m)
    st_folium(m, width=1100, height=560)

with tab2:
    st.subheader("Demand vs Supply Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Load Status Distribution**")
        load_counts = isochrones["load_status"].value_counts().reset_index()
        load_counts.columns = ["Status", "Count"]
        st.dataframe(load_counts, use_container_width=True)
        
        st.markdown("**Population Stats**")
        st.dataframe(
            isochrones[["name","pop_served","load_status"]]
            .sort_values("pop_served", ascending=False)
            .head(10)
            .reset_index(drop=True),
            use_container_width=True
        )
    
    with col2:
        st.markdown("**Key Findings**")
        st.info("""
        - 94 facilities are overloaded (serving >1.5x median population)
        - 65 facilities are underutilized (serving <0.5x median population)
        - Average population per facility: 10,258
        - Most overloaded facility serves 161,624 people
        - Facilities are concentrated in central Kolkata
        - Peripheral areas — south, east, north — are severely underserved
        """)
        
        st.markdown("**Methodology**")
        st.warning("""
        - Travel time: 15 min threshold, 25 km/h average speed
        - Mode: private vehicle / auto-rickshaw
        - Population: WorldPop 2020 UNadj constrained (100m resolution)
        - Total population: 4,878,450
        - Assignment: nearest-neighbour Voronoi approach
        """)

with tab3:
    st.subheader("Proposed Facility Locations & Impact")
    
    baseline_unserved = 3_910_393
    total_pop = 4_878_450
    baseline_coverage = 19.8
    
    facility_data = [
        {"pop_gain": 1_030_307, "cumulative": 1_030_307, "coverage": 40.9},
        {"pop_gain": 1_005_734, "cumulative": 2_036_042, "coverage": 61.5},
        {"pop_gain": 982_589,  "cumulative": 3_018_631, "coverage": 81.7},
    ]
    
    for i, (row, data) in enumerate(zip(proposed.itertuples(), facility_data)):
        with st.expander(f"Facility {i+1} — {data['pop_gain']:,.0f} people newly served", expanded=True):
            col1, col2, col3 = st.columns(3)
            col1.metric("People Newly Served", f"{data['pop_gain']:,.0f}")
            col2.metric("Cumulative Coverage", f"{data['coverage']:.1f}%")
            col3.metric("Coverage Gain", f"+{data['coverage'] - baseline_coverage:.1f}%")
            st.write(f"Location: ({row.geometry.y:.4f}°N, {row.geometry.x:.4f}°E)")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    col1.metric("Coverage Before", "19.8%")
    col2.metric("Coverage After 3 Facilities", "81.7%")
    
    st.success("""
    **Decision: All 3 facilities are justified.**
    
    Facility 1 adds 1,030,307 people to coverage — clear priority.
    Facility 2 adds 1,005,734 — marginal drop of only 2.4%, still high impact.
    Facility 3 adds 982,589 — further 2.3% drop, but brings coverage to 81.7%.
    
    Return diminishes slightly with each facility but remains substantial.
    All 3 placements are recommended given the scale of the access gap.
    """)
    
    st.warning("""
    **Limitations:** 
    Speed assumption (25 km/h) does not account for peak-hour congestion.
    Facility capacity data unavailable — load is estimated by population proximity only.
    Proposed locations are road-network candidates, not assessed for land availability.
    """)
