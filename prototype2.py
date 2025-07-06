"""
Python file for Prototype 2 of the model that allows users to simulate the effects of increased EV uptake
on electricity demand in New Zealand, based on selected charging behaviour.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import helper
import matplotlib as plt
import helper
import json
import streamlit_folium
import folium
import geopandas as gpd
from shapely.geometry import Point
from datetime import datetime, timedelta

# Setup the UI and UI size, such as the title and columns
st.set_page_config(layout="wide")
st.title("Interactive Electricity Grid Model - Prototype 2")
col1, col2 = st.columns([0.5, 0.5])

# Load all relevant data
data_dir = "Data/"
fleet_df = helper.load_file(f"{data_dir}Fleet-31Mar2025.csv")
march_demand_df = helper.load_file(f"{data_dir}Demand_trends_zone_202503.csv", 11)
march_generation_df = helper.load_file(f"{data_dir}202503_Generation_MD.csv")
region_path = f"{data_dir}WGS84_GeoJSON_Zone.JSON"

# Code for displaying the  electricity demand and supply graph

# Process/prepare the generation dataframe
# Clean the trading period columns, including converting units to MWh
march_generation_df = march_generation_df.drop(columns=["TP49", "TP50"])
tp_cols = [col for col in march_generation_df.columns if col.startswith("TP")]
march_generation_df[tp_cols] = march_generation_df[tp_cols] / 1000

# Convert to long format
supply_long = march_generation_df.melt(
    id_vars=["Trading_Date"],
    value_vars=tp_cols,
    var_name="Trading_Period",
    value_name="MWh"
)
# Account for NaN values in the new column
supply_long["MWh"] = supply_long["MWh"].fillna(0)

# Group by date and get the total supply per date, then calculate the peak, average and minimum values and dates that they fall on
march_supply_by_day = supply_long.groupby("Trading_Date")["MWh"].sum()

peak_day = march_supply_by_day.idxmax()
peak_value = march_supply_by_day.max()

average_value = march_supply_by_day.mean()
average_day = (march_supply_by_day - average_value).abs().idxmin()

min_day = march_supply_by_day.idxmin()
min_value = march_supply_by_day.min()

# Expand the supply data into wide format, with each trading date having multiple trading period columns
supply_by_date_period = supply_long.groupby(["Trading_Date", "Trading_Period"])["MWh"].sum().reset_index()
supply_by_date_period = (supply_by_date_period.pivot(index="Trading_Date", columns="Trading_Period", values="MWh"))
supply_by_date_period = supply_by_date_period[
    sorted(supply_by_date_period.columns, key=lambda x: int(x[2:]))
]
supply_by_date_period = supply_by_date_period.reset_index()

# Process the electricity demand dataframe, including converting the units to MWh and creating two new columns for trading dates and periods
march_demand_df["Demand (MWh)"] = march_demand_df["Demand (GWh)"] * 1000
march_demand_df[["Trading_Date", "Trading_Period"]] = march_demand_df["Period start"].str.split(" ", expand=True)

# Group the data by date and period, with an associated total demand
total_demand = (
    march_demand_df.groupby(["Trading_Date", "Trading_Period"])["Demand (MWh)"].sum().reset_index()
)

# Expand the demand data to wide format, with each trading date having rows for trading period and demand values
wide_demand = total_demand.pivot(index="Trading_Date", columns="Trading_Period", values="Demand (MWh)").reset_index()
wide_demand["Trading_Date"] = pd.to_datetime(wide_demand["Trading_Date"], dayfirst=True).dt.strftime("%Y-%m-%d")

# Find the rows that match the desired user choice for what data to show
desired_supply_row = supply_by_date_period[supply_by_date_period["Trading_Date"] == average_day]
desired_demand_row = wide_demand[wide_demand["Trading_Date"] == average_day]

# Extract the values ready for plotting
supply_values = desired_supply_row.drop(columns="Trading_Date").values.flatten()
demand_values = desired_demand_row.drop(columns="Trading_Date").values.flatten()

# Generate a list of plot time strings
half_hour_times = [
    (datetime.min + timedelta(minutes=i * 30)).strftime("%H:%M")
    for i in range(48)
]

# Create a plot of the electricity demand vs supply
chart_data = pd.DataFrame({
    "Time": half_hour_times,
    "Demand (MWh)": demand_values,
    "Supply (MWh)": supply_values
})

fig = px.line(
    chart_data, 
    x="Time", 
    y=["Demand (MWh)", "Supply (MWh)"],
    range_y=[0, chart_data[["Demand (MWh)", "Supply (MWh)"]].max().max() * 1.1]
)

fig.update_layout(
    xaxis_title="Time",
    yaxis_title="Electricity Amount (MWh)",
    xaxis = dict(
        dtick=6
    )
)

with col1:
    st.subheader("Electricity Supply and Demand in New Zealand by Time")
    st.plotly_chart(fig)


# Code for displaying the interactive map of New Zealand

# Load the GeoJSON electricity grid regions data
with open(region_path) as f:
    region_gj = json.load(f)

# Create a base map
region_map = folium.Map(location=[-41, 174], zoom_start=5, height="700px")
folium.GeoJson(
    region_gj,
    tooltip=folium.GeoJsonTooltip(
        fields=["Region"],
        aliases=["Region"],
        localize=True
    )
).add_to(region_map)

# Display the map in Streamlit
with col2:
    result = streamlit_folium.st_folium(region_map, width=700, height=700)

# Get the fleet data and map that shows current territorial authorities
fleet_df_2025 = helper.load_file(f"{data_dir}Fleet-31Mar2025.csv")
ta_path =  f"{data_dir}territorial-authority-2025.json"
ta_gdf = gpd.read_file(ta_path)
region_gdf = gpd.read_file(region_path)

# Prepare the data, including converting to the same CRS and ensuring that the geometry is valid
ta_gdf = ta_gdf.to_crs(epsg=4326)
region_gdf = region_gdf.to_crs(epsg=4326)
region_gdf["geometry"] = region_gdf.buffer(0)

# Spatial join the territorial authority and region data
ta_with_regions = gpd.sjoin(ta_gdf, region_gdf, how="left", predicate="intersects")

# Map the territorial authorities to the right regions, including handling uppercase words
ta_region_map = dict(zip(ta_with_regions["TA2025_V_2"], ta_with_regions["Region"]))
ta_region_map = {
    k.upper(): v.upper()
    for k, v in ta_region_map.items()
}
fleet_df_2025["REGION"] = fleet_df_2025["TLA"].map(ta_region_map)

print(fleet_df_2025.head())

# Handle interactivity on the map
matched_region = None
if result["last_clicked"] is not None:
    clicked_point = Point(result["last_clicked"]["lng"], result["last_clicked"]["lat"])
    match = region_gdf[region_gdf.geometry.contains(clicked_point)]
    
    if not match.empty:
        matched_region = match["Region"].iloc[0]

# Show the number of electric vehicles present in the currently selected region
if matched_region is not None:
    num_evs_region = ((fleet_df_2025["MOTIVE_POWER"] == "ELECTRIC") & (fleet_df_2025["REGION"] == matched_region.upper())).sum()
    with col2:
        st.write(f"There are {num_evs_region} electric vehicles in {matched_region}")