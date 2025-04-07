import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import matplotlib.pyplot as plt
from io import StringIO
from streamlit_folium import st_folium

st.set_page_config(layout="wide")
st.title("Water Quality Explorer")

# Upload station and result files
station_file = st.file_uploader("Upload Station Database (e.g., station.csv)", type="csv")
result_file = st.file_uploader("Upload Result Database (e.g., narrowresult.csv)", type="csv")

if station_file and result_file:
    station_df = pd.read_csv(station_file)
    result_df = pd.read_csv(result_file)

    # Clean and prepare data
    result_df['ActivityStartDate'] = pd.to_datetime(result_df['ActivityStartDate'], errors='coerce')
    result_df['ResultMeasureValue'] = pd.to_numeric(result_df['ResultMeasureValue'], errors='coerce')

    # Get list of contaminants
    contaminants = sorted(result_df['CharacteristicName'].dropna().unique())

    # Contaminant selection
    selected_contaminant = st.selectbox("Select a contaminant to display", contaminants)

    # Filter for selected contaminant
    filtered_df = result_df[result_df['CharacteristicName'] == selected_contaminant].dropna(
        subset=["ResultMeasureValue", "ActivityStartDate", "MonitoringLocationIdentifier"]
    )

    # Value range selector
    min_val, max_val = float(filtered_df['ResultMeasureValue'].min()), float(filtered_df['ResultMeasureValue'].max())
    value_range = st.slider("Select value range", min_value=min_val, max_value=max_val, value=(min_val, max_val))

    # Date range selector
    min_date, max_date = filtered_df['ActivityStartDate'].min(), filtered_df['ActivityStartDate'].max()
    date_range = st.date_input("Select date range", value=(min_date, max_date))

    # Filter by range
    mask = (
        (filtered_df['ResultMeasureValue'] >= value_range[0]) &
        (filtered_df['ResultMeasureValue'] <= value_range[1]) &
        (filtered_df['ActivityStartDate'] >= pd.to_datetime(date_range[0])) &
        (filtered_df['ActivityStartDate'] <= pd.to_datetime(date_range[1]))
    )
    filtered_df = filtered_df[mask]

    # Get qualifying station IDs
    qualifying_sites = filtered_df['MonitoringLocationIdentifier'].unique()
    site_df = station_df[station_df['MonitoringLocationIdentifier'].isin(qualifying_sites)].dropna(
        subset=["LatitudeMeasure", "LongitudeMeasure"]
    )

    # ---------------- Map Plot ----------------
    st.subheader("Map of Stations with Contaminant in Selected Range and Time Frame")
    m = folium.Map(location=[site_df["LatitudeMeasure"].mean(), site_df["LongitudeMeasure"].mean()], zoom_start=7)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in site_df.iterrows():
        folium.Marker(
            location=[row["LatitudeMeasure"], row["LongitudeMeasure"]],
            popup=f"{row['MonitoringLocationName']} ({row['MonitoringLocationIdentifier']})",
            tooltip=row["MonitoringLocationTypeName"]
        ).add_to(marker_cluster)

    st_data = st_folium(m, width=700, height=500)

    # ---------------- Trend Plot ----------------
    st.subheader(f"Trend of {selected_contaminant} Over Time at Selected Sites")
    fig, ax = plt.subplots(figsize=(12, 6))

    for site, site_data in filtered_df.groupby("MonitoringLocationIdentifier"):
        site_data = site_data.sort_values("ActivityStartDate")
        ax.plot(site_data['ActivityStartDate'], site_data['ResultMeasureValue'], label=site, marker='o', linestyle='-')

    ax.set_title(f"{selected_contaminant} Over Time by Site")
    ax.set_xlabel("Date")
    ax.set_ylabel("Measured Value")
    ax.legend(title="Site", bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True)
    st.pyplot(fig)
