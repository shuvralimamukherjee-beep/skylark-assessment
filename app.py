
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

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Facilities", len(facilities))
    col2.metric("Population With Access", "20.2%")
    col3.metric("Population Without Access", "3,991,826")

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
            name="Unserved Areas",
            tooltip="Unserved Area"
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
                popup=f"PROPOSED: {row['facility_id']}<br>Est. {row['pop_gain']:,.0f} people served"
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

    with col2:
        st.markdown("**Population Stats**")
        st.dataframe(
            isochrones[["name", "pop_served", "load_status"]]
            .sort_values("pop_served", ascending=False)
            .head(10)
            .reset_index(drop=True),
            use_container_width=True
        )

    st.markdown("---")
    st.markdown("**Methodology Note**")
    st.info(
        "Population assigned to nearest facility using Voronoi-style nearest-neighbour assignment. "
        "Overloaded = >1.5x median load. Underutilized = <0.5x median load. "
        "Speed assumption: 25 km/h (conservative for Kolkata peak traffic). "
        "Population data: WorldPop 2020 proxy grid (500m resolution, uniform distribution)."
    )

with tab3:
    st.subheader("Proposed Facility Locations & Impact")

    st.markdown("Up to 3 new facilities proposed to maximise population brought within 15-minute access.")

    cumulative = 0
    baseline_unserved = 3_991_826

    for i, row in proposed.iterrows():
        cumulative += row["pop_gain"]
        pct_improvement = (row["pop_gain"] / baseline_unserved) * 100

        with st.expander(f"Facility {i+1} — {row['pop_gain']:,.0f} people newly served", expanded=True):
            col1, col2 = st.columns(2)
            col1.metric("Additional People Served", f"{row['pop_gain']:,.0f}")
            col2.metric("% of Unserved Population", f"{pct_improvement:.1f}%")
            st.write(f"Location: ({row.geometry.y:.4f}°N, {row.geometry.x:.4f}°E)")

    st.markdown("---")
    st.success(
        f"3 facilities bring **{cumulative:,.0f} additional people** within 15-min access. "
        f"Coverage improves from 20.2% to ~67%. "
        f"Remaining unserved: {baseline_unserved - cumulative:,.0f} people."
    )
    st.warning(
        "Marginal return is similar across all 3 facilities due to uniform population grid. "
        "With ward-level census data, placement would be more precise. "
        "This is acknowledged as a limitation of the current data approach."
    )
