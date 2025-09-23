"""
Python file for Prototype 2 of the model that allows users to simulate the effects of increased EV uptake
on electricity demand in New Zealand, based on selected charging behaviour.
"""

# Import all necessary libraries/dependencies
import streamlit as st
import pandas as pd
import plotly.express as px
import helper
import json
import streamlit_folium
import folium
import geopandas as gpd
from shapely.geometry import Point
from geopandas import GeoDataFrame
from datetime import datetime, timedelta
import numpy as np

# Setup the UI and UI size, such as the title and columns
st.set_page_config(layout="wide")
st.markdown("""
    <style>
    iframe {
        height: 800px !important;
        max-height: 800px !important;
    }
    </style>
""", unsafe_allow_html=True)
st.title("Interactive Electricity Grid Model - Prototype 2")
col1, col2 = st.columns([0.5, 0.5])

# Define paths for and load relevant data
data_dir = "Data/"
fleet_df = helper.load_file(f"{data_dir}Fleet-31Mar2025.csv")
march_generation_df = helper.load_file(f"{data_dir}202503_Generation_MD.csv")
network_mapping_df = helper.load_file(f"{data_dir}20250614_NetworkSupplyPointsTable.csv")
ta_path =  f"{data_dir}territorial-authority-2025.json"

# Variable for tracking which region has been selected 
selected_region = "New Zealand"

# Code for displaying the interactive map of New Zealand

# Display the map in Streamlit
with col2:

    is_territorial_view = st.toggle("Territorial Authority View", value=False)

    if is_territorial_view == False:
        march_demand_df = helper.load_file(f"{data_dir}Demand_trends_zone_202503.csv", 11)
        region_path = f"{data_dir}WGS84_GeoJSON_Zone.JSON"

    elif is_territorial_view == True:
        march_demand_df = helper.load_file(f"{data_dir}Demand_trends_node_202503.csv", 11)
        region_path = f"{data_dir}territorial-authority-2025.json"

    region_gdf = gpd.read_file(region_path)

    with open(region_path, encoding="utf-8") as f:
      region_gj = json.load(f)

    for feature in region_gj["features"]:
        props = feature["properties"]
        if "TA2025_V_1" in props:
            props["Region"] = props["TA2025_V_1"]
            del props["TA2025_V_1"]

    # Create a base map
    region_map = folium.Map(
            location=[-42.5, 174], 
            zoom_start=6, 
            dragging=False,
            zoom_control=False,
            scrollWheelZoom=False, 
            doubleClickZoom=False, 
        )
    folium.GeoJson(
        region_gj,
        tooltip=folium.GeoJsonTooltip(
            fields=["Region"],
            aliases=["Region"],
            localize=True
        )
    ).add_to(region_map)


    result = streamlit_folium.st_folium(region_map, width=1000, height=1000, key="nzmap")


# Use helper functions to map territorial authority data to regions, load the fleet data , and build the fleet summary dataframe
ta_region_map = helper.get_ta_region_map(ta_path, region_gdf)
fleet_df_2025 = helper.get_cleaned_fleet_df(f"{data_dir}Fleet-31Mar2025.csv", ta_region_map)
region_fleet_df = helper.build_region_fleet_summary(fleet_df_2025, is_territorial_view)

# Handle interactivity on the map
if result["last_clicked"] is not None:
    clicked_point = Point(result["last_clicked"]["lng"], result["last_clicked"]["lat"])
    match = region_gdf[region_gdf.geometry.contains(clicked_point)]
    
    if not match.empty:
        if is_territorial_view == False:
            selected_region = match["Region"].iloc[0]
        elif is_territorial_view == True:
            selected_region = match["TA2025_V_1"].iloc[0]

    if selected_region == "Area Outside Territorial Authority":
        st.error(f"The selected region '{selected_region}' is not valid.")
        st.stop()

# Get the electric vehicle counts for the current region
light_evs_region = region_fleet_df.loc[selected_region.upper(), "Light Electric Vehicle Count"]
heavy_evs_region = region_fleet_df.loc[selected_region.upper(), "Heavy Electric Vehicle Count"]
num_evs_region = light_evs_region + heavy_evs_region

# Display the number of electric vehicles in the region, including the most common light and heavy electric vehicle make and model
with col2:
    st.write(f"There are {num_evs_region} electric vehicles in {selected_region}")

    light_ev_df = fleet_df_2025[helper.get_electric_mask(fleet_df_2025) & 
                        (fleet_df_2025["GROSS_VEHICLE_MASS"] < 3500)]
    
    heavy_ev_df = fleet_df_2025[helper.get_electric_mask(fleet_df_2025) & 
                            (fleet_df_2025["GROSS_VEHICLE_MASS"] > 3500)]
    
    heavy_ev_df["MAKE_MODEL"] = heavy_ev_df["MAKE"] + " " + heavy_ev_df["MODEL"]
    light_ev_df["MAKE_MODEL"] = light_ev_df["MAKE"] + " " + light_ev_df["MODEL"]

    most_common_heavy_ev = heavy_ev_df["MAKE_MODEL"].mode()[0]
    year_common_heavy_ev = heavy_ev_df[
        heavy_ev_df["MAKE_MODEL"] == most_common_heavy_ev
    ]["VEHICLE_YEAR"].mode()[0]

    st.write(f"The most common heavy EV is the {year_common_heavy_ev} {most_common_heavy_ev}")

    most_common_light_ev = light_ev_df["MAKE_MODEL"].mode()[0]
    year_common_light_ev = light_ev_df[
        light_ev_df["MAKE_MODEL"] == most_common_light_ev
    ]["VEHICLE_YEAR"].mode()[0]

    st.write(f"The most common light EV is the {year_common_light_ev} {most_common_light_ev}")


# Code for displaying the  electricity demand and supply graph

# Process/prepare the generation dataframe

# Clean the trading period columns, including converting units to MWh
march_generation_df = march_generation_df.drop(columns=["TP49", "TP50"])
tp_cols = [col for col in march_generation_df.columns if col.startswith("TP")]
march_generation_df[tp_cols] = march_generation_df[tp_cols] / 1000


# Join the demand dataframe to the network supply points table dataframe so that NZTM location data can be used to map generation data to specific regions

# Make the key columns that are to be joined consistent, then perform a left join on the generation data
network_mapping_df.rename(columns={"POC code" : "POC_Code"}, inplace=True)
network_mapping_df = network_mapping_df.drop_duplicates(subset="POC_Code")

march_generation_df = march_generation_df.merge(network_mapping_df[["POC_Code", "NZTM easting", "NZTM northing"]], left_on="POC_Code", right_on="POC_Code")

# Define a mapping for handling cases such as where NZTM data is missing in the network supply table, then apply it
override_map = {
    "HRP2201": "Central North Island",
    "JRD1101": "Lower North Island",
    "TAB0331": "Central North Island",
    "TAB2201": "Central North Island",
    "BEN2202": "Lower South Island"
}

condition = march_generation_df["NZTM easting"].isna()
march_generation_df["Region"] = march_generation_df["POC_Code"].map(override_map)

march_generation_df = march_generation_df.dropna(subset=["NZTM easting","NZTM northing"]).copy()
march_generation_df["geometry"] = gpd.points_from_xy(march_generation_df["NZTM easting"], march_generation_df["NZTM northing"])


# Create a geodataframe so that we can map the generation data to each of the NZ regions
generation_gdf = GeoDataFrame(
    data = march_generation_df,
    geometry = march_generation_df["geometry"],
    crs = "EPSG:2193"
)
generation_gdf = generation_gdf.to_crs(epsg=4326)

result_gdf = gpd.sjoin(generation_gdf, region_gdf, how="left", predicate="within")

# Process the dataframes, including handling duplicates
if is_territorial_view == False:
    region_lookup = result_gdf.drop_duplicates(subset="POC_Code")[["POC_Code", "Region_right"]]
    march_generation_df = march_generation_df.merge(region_lookup, on="POC_Code", how="left")
    march_generation_df["Region"] = march_generation_df["Region"].fillna(march_generation_df.pop("Region_right")) 

if is_territorial_view == True:
    result_gdf["Region"] = result_gdf["TA2025_V_1"]
    result_gdf = result_gdf.drop(columns=["TA2025_V_2"])
    region_lookup = result_gdf
    march_generation_df = region_lookup


# Filter generation by region
if selected_region != "New Zealand":
    march_generation_df = march_generation_df[march_generation_df["Region"] == selected_region]

# Convert supply data to long format
supply_long = march_generation_df.melt(
    id_vars=["Trading_Date"],
    value_vars=tp_cols,
    var_name="Trading_Period",
    value_name="MWh"
)
# Account for NaN values in the new column
supply_long["MWh"] = supply_long["MWh"].fillna(0)

# Group by date and get the total supply per date, then calculate the peak, average, and minimum values and dates that they fall on
march_supply_by_day = supply_long.groupby("Trading_Date")["MWh"].sum()

# peak_day = march_supply_by_day.idxmax()
# peak_value = march_supply_by_day.max()

# average_value = march_supply_by_day.mean()
# average_day = (march_supply_by_day - average_value).abs().idxmin()

# min_day = march_supply_by_day.idxmin()
# min_value = march_supply_by_day.min()

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

# Handle mapping the demand data to a specific territorial authority if needed
if is_territorial_view == True:
    march_demand_df = march_demand_df.merge(network_mapping_df[["POC_Code", "NZTM easting", "NZTM northing"]], left_on="Region ID", right_on="POC_Code")

    march_demand_df["geometry"] = gpd.points_from_xy(march_demand_df["NZTM easting"], march_demand_df["NZTM northing"])

    # Create a geodataframe so that we can map the demand data to each of the NZ regions
    demand_gdf = GeoDataFrame(
        data = march_demand_df,
        geometry = march_demand_df["geometry"],
        crs = "EPSG:2193"
    )
    demand_gdf = demand_gdf.to_crs(epsg=4326)

    result_gdf = gpd.sjoin(demand_gdf, region_gdf, how="left", predicate="within")
    result_gdf["Region"] = result_gdf["TA2025_V_1"]
    march_demand_df = result_gdf


# Filter demand by region
if selected_region != "New Zealand":
    march_demand_df = march_demand_df[march_demand_df["Region"] == selected_region]

# Group the data by date and period, with an associated total demand
total_demand = (
    march_demand_df.groupby(["Trading_Date", "Trading_Period"])["Demand (MWh)"].sum().reset_index()
)

# Expand the demand data to wide format, with each trading date having rows for trading period and demand values
wide_demand = total_demand.pivot(index="Trading_Date", columns="Trading_Period", values="Demand (MWh)").reset_index()
wide_demand["Trading_Date"] = pd.to_datetime(wide_demand["Trading_Date"], dayfirst=True).dt.strftime("%Y-%m-%d")

# Create filtered datasets that only show data on weekdays
wide_demand["Trading_Date"]  = pd.to_datetime(wide_demand["Trading_Date"])

supply_by_date_period["Trading_Date"]  = pd.to_datetime(supply_by_date_period["Trading_Date"])

with col1:
    day_options = ["Mon", "Tues", "Wed", "Thurs", "Fri", "Sat", "Sun"]
    selected_day = st.selectbox(label="Day selector", options=day_options)

# Get average electricity demand and supply data/profiles using a helper functoin
demand_values, supply_values = helper.get_avg_profiles(
    day_options.index(selected_day),
    supply_by_date_period,
    wide_demand
)

# Generate a list of plot time strings
half_hour_times = [
    (datetime.min + timedelta(minutes=i * 30)).strftime("%H:%M")
    for i in range(48)
]

if demand_values.empty:
    demand_values = pd.Series([0] * 48)

if supply_values.empty:
    supply_values = pd.Series([0] * 48)

# Create a plot of the electricity demand vs supply
chart_data = pd.DataFrame({
    "Time": half_hour_times,
    "Demand (MWh)": demand_values.values,
    "Supply (MWh)": supply_values.values
})

# Only show the relevant data for the selected region
filtered_region_fleet = region_fleet_df.loc[selected_region.upper()]

# Calculate the existing/current amount of light and heavy electric vehicle proportions 
current_light_ev_share = (filtered_region_fleet["Light Electric Vehicle Count"] / (filtered_region_fleet["Light Electric Vehicle Count"] + filtered_region_fleet["Light Combustion Vehicle Count"])) * 100
current_heavy_ev_share = (filtered_region_fleet["Heavy Electric Vehicle Count"] / (filtered_region_fleet["Heavy Electric Vehicle Count"] + filtered_region_fleet["Heavy Combustion Vehicle Count"])) * 100

# Handle changing electric vehicle uptake
with col1:
    st.subheader(f"Average Electricity Supply and Demand by Time for {selected_region}")

    # Define a selection box for charging behaviour configuration/interactivity
    charging_scenarios = ["Status-quo", "Daytime-priority"]
    charging_behaviour = st.selectbox("Charging Behaviour", charging_scenarios)

    # Define sliders for changing uptake
    target_light_ev_pct = st.slider("Light EV uptake (%)", value=current_light_ev_share, min_value=0.00, max_value=100.00)
    target_heavy_ev_pct = st.slider("Heavy EV uptake (%)", value=current_heavy_ev_share, min_value=0.00, max_value=100.00)

    # Define a number input for setting the "compliance" rate (The percentage of people who follow the user-specified charging pattern)
    current_compliance = st.number_input("Compliance rate (%)", value=100, min_value=0, max_value=100)

    # Define a slider for increasing existing electricity supply (I.e expanding grid generation and infrastructure)
    supply_expansion = st.slider("Increase in electricity supply (%)", value=0.00, min_value=0.00, max_value=100.00)

    supply_values = (1 + supply_expansion / 100) * supply_values

    # Calculate the number of vehicles needed to reach each specified uptake target
    needed_light_ev = (target_light_ev_pct / 100) * (filtered_region_fleet["Light Electric Vehicle Count"] + filtered_region_fleet["Light Combustion Vehicle Count"]) - filtered_region_fleet["Light Electric Vehicle Count"]
    needed_heavy_ev = (target_heavy_ev_pct / 100) * (filtered_region_fleet["Heavy Electric Vehicle Count"] + filtered_region_fleet["Heavy Combustion Vehicle Count"]) - filtered_region_fleet["Heavy Electric Vehicle Count"]

    # Estimate the needed kWh by approximating the efficiencies of reference electric vehicles - see dissertation for explanation
    # TODO REMOVE PLACEHOLDER VALUES 
    light_ev_efficiency = 0.18
    heavy_ev_efficiency = 0.80

    daily_km_light_ev = 30
    daily_km_heavy_ev = 300

    kWh_day_light = daily_km_light_ev * light_ev_efficiency
    kWh_day_heavy = daily_km_heavy_ev * heavy_ev_efficiency

    extra_kWh_day = needed_light_ev * kWh_day_light + needed_heavy_ev * kWh_day_heavy

    # Divide the needed extra electricity across the relevant daily profile/scenario
    if charging_behaviour == "Status-quo":
        # Night charging: 18:00–24:00 and 00:00–07:00
        profile = np.zeros(48)
        profile[36:48] = 1 
        profile[0:14]  = 1
        profile = profile / profile.sum()

    elif charging_behaviour == "Daytime-priority":
        profile = np.zeros(48)
        profile[16:34] = 1
        profile = profile / profile.sum()

    # Define non-compliance to be random charging across the whole day
    random_profile = np.random.random(48)
    random_profile = random_profile / random_profile.sum()

    # Account for the compliance rate
    c = current_compliance / 100.0
    effective_profile = c * profile + (1 - c) * random_profile
    effective_profile = effective_profile / effective_profile.sum()

    # Allocate the additional needed energy
    extra_MWh_per_slot = (extra_kWh_day / 1000.0) * effective_profile

    # Update the data and plot the chart with the new values
    new_demand_values = demand_values.values + extra_MWh_per_slot
    chart_data = pd.DataFrame({
        "Time": half_hour_times,
        "Demand (MWh)": new_demand_values,
        "Supply (MWh)": supply_values.values
    })
    fig = px.line(chart_data, x="Time", y=["Demand (MWh)", "Supply (MWh)"], color_discrete_sequence=["#E69F00", "#0072B2"])

    fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Electricity Amount (MWh)",
            xaxis = dict(
                dtick=6
            ),
            height=600
        )

    st.plotly_chart(fig)