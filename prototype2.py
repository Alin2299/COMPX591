"""
Python file for Prototype 2 of the model that allows users to simulate the effects of increased EV uptake and other scenarios
on electricity demand and supply in New Zealand, based on selected charging behaviour and various other parameters
"""

# Import all necessary libraries and dependencies
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

# The code section below defines the page UI, layout, and other meta information
st.set_page_config(layout="wide")

# Define a section for providing some general information and help for the tool
with st.expander("ℹ️ About this app"):
    st.markdown("""
        This interactive prototype tool explores how various scenarios, including electric vehicle (EV) uptake, affect
        electricity demand and supply in  New Zealand. It allows users to simulate 
        different charging behaviours, EV adoption rates, infrastructure 
        expansion scenarios, and various other parameters, and then observe how these factors influence  
        national and regional electricity load profiles over time.

        The model, which was developed in Python, draws on publicly available datasets from sources such as the Electricity Authority 
        and the New Zealand Transport Agency. It is designed as an exploratory prototype rather 
        than a purely predictive or statistical model, and the overall goal is to help policymakers, researchers, and the public 
        better understand the scale and timing of changes that are likely to occur as 
        New Zealand eventually transitions to a low-emissions economy and energy sector.
                
        Additionally, it also serves to translate theoretical research into a practical and accessible format, and lay the groundwork for future relevant work.
                
        Available EV charging scenarios in this version:
        - Status-quo scenario: This scenario assumes a status-quo situation in which EV charging happens during evening-hours, defined as 
        6pm to 7am.
        - Daytime-priority: This scenario assumes that charging takes place primarily during daylight hours, defined as 9am to 5pm (for example, workplace and solar charging)
                
        For the purposes of this model, a 2017 Nissan Leaf and 2022 CRRC ET12MAX electric bus are used as references
        for calculating and modelling the demand for light and heavy EV uptake respectively, due to the unwieldy amount
        of possible combinations of EV year, make, and models - in particular, these two vehicles were found to be the most 
        common EV of their respective weight class in New Zealand, with 3500kg as the split between light and heavy vehicles.
        Additionally, we define electric vehicles to not only include fully battery electric vehicles, but also plug-in hybrids.
                
        The option to print the page out as a PDF and therefore save the plot is available through the 3-dot menu on the top-right of the page.
                
        This research project was developed for the COMPX591 - Dissertation paper at the University of Waikato, as part of a BSc with Honours in Computer Science in 2025.     
        For comments or questions, please email andrewlin125@gmail.com.
    """)

# Define an appropriate layout and size constraints
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

# Load relevant data from their stored paths using a helper function
data_dir = "Data/"
march_generation_df = helper.load_file(f"{data_dir}202503_Generation_MD.csv")
network_mapping_df = helper.load_file(f"{data_dir}20250614_NetworkSupplyPointsTable.csv")
ta_path =  f"{data_dir}territorial-authority-2025.json"

# Variable for tracking which region is currently selected 
selected_region = "New Zealand"

# The code below displays the interactive map of New Zealand

# Wrap the code in a spinner for a better user experience
with st.spinner("Please wait..."):
    # Display the map in Streamlit using the appropriate column
    with col2:

        # Handle which view of the map to display, either territorial authority or electricity grid zone
        is_territorial_view = st.toggle("Territorial Authority View", value=False)

        if is_territorial_view == False:
            march_demand_df = helper.load_file(f"{data_dir}Demand_trends_zone_202503.csv", 11)
            region_path = f"{data_dir}WGS84_GeoJSON_Zone.JSON"

        elif is_territorial_view == True:
            march_demand_df = helper.load_file(f"{data_dir}Demand_trends_node_202503.csv", 11)
            region_path = f"{data_dir}territorial-authority-2025.json"

        # Read and process the relevant region geodataframe appropriately
        region_gdf = gpd.read_file(region_path)

        with open(region_path, encoding="utf-8") as f:
            region_gj = json.load(f)

        for feature in region_gj["features"]:
            props = feature["properties"]
            if "TA2025_V_1" in props:
                props["Region"] = props["TA2025_V_1"]
                del props["TA2025_V_1"]

        # Create the base map using Folium
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

    # Use helper functions to map territorial authority data to regions, load the fleet data (based on the ta region map), and build the fleet summary dataframe
    ta_region_map = helper.get_ta_region_map(ta_path, region_gdf)
    fleet_df_2025 = helper.get_cleaned_fleet_df(f"{data_dir}Fleet-31Mar2025.csv", ta_region_map)
    region_fleet_df = helper.build_region_fleet_summary(fleet_df_2025, is_territorial_view)

    # Handle interactivity on the map, including with both map view variants
    if result["last_clicked"] is not None:
        clicked_point = Point(result["last_clicked"]["lng"], result["last_clicked"]["lat"])
        match = region_gdf[region_gdf.geometry.contains(clicked_point)]
        
        if not match.empty:
            if is_territorial_view == False:
                selected_region = match["Region"].iloc[0]
            elif is_territorial_view == True:
                selected_region = match["TA2025_V_1"].iloc[0]

        # Handle the edge case where the region is invalid
        if selected_region == "Area Outside Territorial Authority":
            st.error(f"The selected region '{selected_region}' is not valid.")
            st.stop()

    # The code below preprocesses the electricity generation dataframe and other data, for eventual visualisation

    # Clean the trading period columns, including converting the units to MWh
    march_generation_df = march_generation_df.drop(columns=["TP49", "TP50"])
    tp_cols = [col for col in march_generation_df.columns if col.startswith("TP")]
    march_generation_df[tp_cols] = march_generation_df[tp_cols] / 1000

    # Make key columns consistent, then perform a left join on the generation data and network supply points dataframe, so as to map generation to the regions
    network_mapping_df.rename(columns={"POC code" : "POC_Code"}, inplace=True)
    network_mapping_df = network_mapping_df.drop_duplicates(subset="POC_Code")

    march_generation_df = march_generation_df.merge(network_mapping_df[["POC_Code", "NZTM easting", "NZTM northing"]], left_on="POC_Code", right_on="POC_Code")

    # Define a manual mapping for handling edge or unexpected cases, such as where NZTM data is missing in the network supply table, then apply it
    override_map = {
        "HRP2201": "Central North Island",
        "JRD1101": "Lower North Island",
        "TAB0331": "Central North Island",
        "TAB2201": "Central North Island",
        "BEN2202": "Lower South Island"
    }

    condition = march_generation_df["NZTM easting"].isna()
    march_generation_df["Region"] = march_generation_df["POC_Code"].map(override_map)

    # Clean the dataframe, then create a new temporary column to assist with mapping
    march_generation_df = march_generation_df.dropna(subset=["NZTM easting","NZTM northing"]).copy()
    march_generation_df["geometry"] = gpd.points_from_xy(march_generation_df["NZTM easting"], march_generation_df["NZTM northing"])

    # Create a geodataframe so that the generation data can be mapped to each of the NZ regions using sjoin
    generation_gdf = GeoDataFrame(
        data = march_generation_df,
        geometry = march_generation_df["geometry"],
        crs = "EPSG:2193"
    )
    generation_gdf = generation_gdf.to_crs(epsg=4326)

    result_gdf = gpd.sjoin(generation_gdf, region_gdf, how="left", predicate="within")

    # Process the generation dataframe appropriately depending on the current map variant view, including handling duplicates
    if is_territorial_view == False:
        region_lookup = result_gdf.drop_duplicates(subset="POC_Code")[["POC_Code", "Region_right"]]
        march_generation_df = march_generation_df.merge(region_lookup, on="POC_Code", how="left")
        march_generation_df["Region"] = march_generation_df["Region"].fillna(march_generation_df.pop("Region_right")) 

    if is_territorial_view == True:
        result_gdf["Region"] = result_gdf["TA2025_V_1"]
        result_gdf = result_gdf.drop(columns=["TA2025_V_2"])
        region_lookup = result_gdf
        march_generation_df = region_lookup

    # Filter the generation data by the currently selected region
    if selected_region != "New Zealand":
        march_generation_df = march_generation_df[march_generation_df["Region"] == selected_region]

    # Convert the electricity supply/generation data to long format
    supply_long = march_generation_df.melt(
        id_vars=["Trading_Date"],
        value_vars=tp_cols,
        var_name="Trading_Period",
        value_name="MWh"
    )
    # Account for NaN values in the new column
    supply_long["MWh"] = supply_long["MWh"].fillna(0)

    # Group by date and get the total supply per date
    march_supply_by_day = supply_long.groupby("Trading_Date")["MWh"].sum()

    # Convert the supply data into wide format, with each trading date having multiple trading period columns
    supply_by_date_period = supply_long.groupby(["Trading_Date", "Trading_Period"])["MWh"].sum().reset_index()
    supply_by_date_period = (supply_by_date_period.pivot(index="Trading_Date", columns="Trading_Period", values="MWh"))
    supply_by_date_period = supply_by_date_period[
        sorted(supply_by_date_period.columns, key=lambda x: int(x[2:]))
    ]
    supply_by_date_period = supply_by_date_period.reset_index()

    # Process the electricity demand dataframe, including converting the units to MWh and creating two columns for trading dates and periods
    march_demand_df["Demand (MWh)"] = march_demand_df["Demand (GWh)"] * 1000
    march_demand_df[["Trading_Date", "Trading_Period"]] = march_demand_df["Period start"].str.split(" ", expand=True)

    # Handle mapping the demand data to a specific territorial authority if needed
    if is_territorial_view == True:
        # Merge the demand dataframe with the network mapping dataframe and create a temporary column for assisting with the mapping process
        march_demand_df = march_demand_df.merge(network_mapping_df[["POC_Code", "NZTM easting", "NZTM northing"]], left_on="Region ID", right_on="POC_Code")
        march_demand_df["geometry"] = gpd.points_from_xy(march_demand_df["NZTM easting"], march_demand_df["NZTM northing"])

        # Create a geodataframe so that we can map the demand data to each of the NZ regions, and apply other processing
        demand_gdf = GeoDataFrame(
            data = march_demand_df,
            geometry = march_demand_df["geometry"],
            crs = "EPSG:2193"
        )
        demand_gdf = demand_gdf.to_crs(epsg=4326)

        result_gdf = gpd.sjoin(demand_gdf, region_gdf, how="left", predicate="within")
        result_gdf["Region"] = result_gdf["TA2025_V_1"]
        march_demand_df = result_gdf

    # Filter demand by the currently selected region
    if selected_region != "New Zealand":
        march_demand_df = march_demand_df[march_demand_df["Region"] == selected_region]

    # Group the data by date and period, with an associated total demand
    total_demand = (
        march_demand_df.groupby(["Trading_Date", "Trading_Period"])["Demand (MWh)"].sum().reset_index()
    )

    # Convert the demand data to wide format, with each trading date having rows for trading period and demand values
    wide_demand = total_demand.pivot(index="Trading_Date", columns="Trading_Period", values="Demand (MWh)").reset_index()
    wide_demand["Trading_Date"] = pd.to_datetime(wide_demand["Trading_Date"], dayfirst=True).dt.strftime("%Y-%m-%d")

    # Define containers for maintaining an appropriate layout, and setup the option to select which weekday to show data for
    with col1:
        chart_container = st.container()
        controls_container = st.container()
        with controls_container:
            day_options = ["Mon", "Tues", "Wed", "Thurs", "Fri", "Sat", "Sun"]
            selected_day = st.selectbox(label="Day selector", options=day_options)

    # Get the electricity demand and supply data in the form of profiles using a helper function
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

    # Handle the case where data is missing (e.g. no demand in a region)
    if demand_values.empty:
        demand_values = pd.Series([0] * 48)

    if supply_values.empty:
        supply_values = pd.Series([0] * 48)

    # Setup the data for the plot of the electricity demand vs supply
    chart_data = pd.DataFrame({
        "Time": half_hour_times,
        "Demand (MWh)": demand_values.values,
        "Supply (MWh)": supply_values.values
    })

    # Only show the relevant fleet data for the currently selected region
    filtered_region_fleet = region_fleet_df.loc[selected_region.upper()]

    # Calculate the existing light and heavy electric vehicle proportions 
    current_light_ev_share = (filtered_region_fleet["Light Electric Vehicle Count"] / (filtered_region_fleet["Light Electric Vehicle Count"] + filtered_region_fleet["Light Combustion Vehicle Count"])) * 100
    current_heavy_ev_share = (filtered_region_fleet["Heavy Electric Vehicle Count"] / (filtered_region_fleet["Heavy Electric Vehicle Count"] + filtered_region_fleet["Heavy Combustion Vehicle Count"])) * 100

    # Display (the rest of) the interactive elements for user scenario simulation
    with col1:
        # Wrap in a container for controlling the layout of the overall column
        with controls_container:
            # Define a selection box for interactively specifying the EV charging behaviour configuration
            charging_scenarios = ["Status-quo", "Daytime-priority"]
            charging_behaviour = st.selectbox("Charging Behaviour", charging_scenarios)

            # Define number inputs for changing the (existing) EV uptake
            target_light_ev_pct = st.number_input(r"Light EV uptake (% of regional light fleet)", value=current_light_ev_share, min_value=0.00, max_value=100.00)
            target_heavy_ev_pct = st.number_input(r"Heavy EV uptake (% of regional heavy fleet)", value=current_heavy_ev_share, min_value=0.00, max_value=100.00)

            # Define a number input for setting the "compliance" rate (the percentage of people who follow the user-specified charging pattern)
            current_compliance = st.number_input(
                "Compliance rate (%)", 
                value=100, 
                min_value=0, 
                max_value=100, 
                help=r"The percentage of people that follow the set charging scenario - non-compliance is defined as convenient charging behaviour")

            # Define columns for laying out the supply expansion controls appropriately
            supply_expansion_col, ratio_col = st.columns([0.7, 0.3])

            # Define a number input for increasing the existing electricity supply (i.e. expanding grid generation and other infrastructure)
            with supply_expansion_col:
                supply_expansion = st.number_input("Increase in electricity supply (%)", value=0.00, min_value=0.00, max_value=100.00)

            # Define a number input for specifying the percentage of new supply as either wind or solar
            with ratio_col:
                wind_solar_ratio = st.number_input(
                    "Wind/Solar Ratio (%)",
                    min_value=0,
                    max_value=100,
                    value=50,
                    step=1,
                    help=r"The percentage of supply expansion allocated to wind vs solar (e.g. 70 = 70% wind, 30% solar)"
                )

            # Create base shapes with 48 half-hour slots
            wind_profile = np.ones(48) # Wind is assumed to be available all day
            solar_profile = np.zeros(48)
            solar_profile[18:34] = 1 # Solar is assumed to be available from 9am–5pm

            # Calculate the raw ratio for new wind vs solar supply expansion
            wind_share = wind_solar_ratio / 100.0
            solar_share = 1 - wind_share

            # Calculate the total new supply to be created, and distribute based on the user-specified ratio
            total_new_supply = (supply_expansion / 100) * supply_values.sum()
            new_wind = wind_share * total_new_supply
            new_solar = solar_share * total_new_supply

            num_active_wind = wind_profile.sum()  
            distributed_wind = wind_profile * (new_wind / num_active_wind)

            num_active_solar = solar_profile.sum()  
            distributed_solar = solar_profile * (new_solar / num_active_solar)

            # Add the final solar and wind supply values to the original supply values
            supply_values = supply_values + distributed_wind + distributed_solar

        # Calculate the number of electric vehicles needed to reach each specified uptake target
        needed_light_ev = (target_light_ev_pct / 100) * (filtered_region_fleet["Light Electric Vehicle Count"] + filtered_region_fleet["Light Combustion Vehicle Count"]) - filtered_region_fleet["Light Electric Vehicle Count"]
        needed_heavy_ev = (target_heavy_ev_pct / 100) * (filtered_region_fleet["Heavy Electric Vehicle Count"] + filtered_region_fleet["Heavy Combustion Vehicle Count"]) - filtered_region_fleet["Heavy Electric Vehicle Count"]

        # Estimate the needed kWh by using the approximate efficiencies of reference electric vehicles, as well as daily travel distance
        light_ev_efficiency = 0.19
        heavy_ev_efficiency = 0.7

        daily_km_light_ev = 40
        daily_km_heavy_ev = 300

        # Calculate the total kWh used per day for each new light and heavy EV, then sum to get the total kWh daily
        kWh_day_light = daily_km_light_ev * light_ev_efficiency
        kWh_day_heavy = daily_km_heavy_ev * heavy_ev_efficiency

        extra_kWh_day = needed_light_ev * kWh_day_light + needed_heavy_ev * kWh_day_heavy

        # Distribute the new required electricity (demand) across the base daily profile according to the selected scenario
        if charging_behaviour == "Status-quo":
            # Night charging is set by the slots 18:00–24:00 and 00:00–07:00
            profile = np.zeros(48)
            profile[36:48] = 1 
            profile[0:14]  = 1
            profile = profile / profile.sum()

        elif charging_behaviour == "Daytime-priority":
            # Day charging is set using the appropriate day slots: 9:00-17:00
            profile = np.zeros(48)
            profile[18:34] = 1
            profile = profile / profile.sum()

        # Define the logic and profile for non-compliance - assume that users prefer charging when they are at home, with some charging around work-hours
        non_compliant_profile = np.zeros(48)
        non_compliant_profile[36:48] = 0.75 
        non_compliant_profile[0:14]  = 0.75 
        non_compliant_profile[14:36]  = 0.25
        non_compliant_profile = non_compliant_profile / non_compliant_profile.sum()

        compliance = current_compliance / 100.0 
        final_profile = compliance * profile + (1 - compliance) * non_compliant_profile

        # Normalise the final profile
        final_profile = final_profile / final_profile.sum()

        # Allocate the additional needed demand, accounting for compliance
        extra_MWh_per_slot = (extra_kWh_day / 1000.0) * final_profile

        # Update the chart data and then plot with new values
        new_demand_values = demand_values.values + extra_MWh_per_slot
        chart_data = pd.DataFrame({
            "Time": half_hour_times,
            "Demand (MWh)": new_demand_values,
            "Supply (MWh)": supply_values.values
        })

        with chart_container:
            # Define the header for the electricity plot 
            st.subheader(f"Average Electricity Supply and Demand by Time for {selected_region}")

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

        # Display some relevant helpful summary information, such as the number of EVs and non-EVs in the region and other measures
        with col2:
            # Get various different vehicle counts for the currently selected region, including EVs, non-EVs, and light vs heavy vehicles
            light_evs_region = region_fleet_df.loc[selected_region.upper(), "Light Electric Vehicle Count"]
            heavy_evs_region = region_fleet_df.loc[selected_region.upper(), "Heavy Electric Vehicle Count"]
            num_evs_region = light_evs_region + heavy_evs_region

            light_combustion_region = region_fleet_df.loc[selected_region.upper(), "Light Combustion Vehicle Count"]
            heavy_combustion_region = region_fleet_df.loc[selected_region.upper(), "Heavy Combustion Vehicle Count"]
            num_combustion_region = light_combustion_region + heavy_combustion_region

            num_light_vehicles = light_evs_region + light_combustion_region
            num_heavy_vehicles = heavy_evs_region + heavy_combustion_region
            num_vehicles_region = num_evs_region + num_combustion_region

            percent_light = (num_light_vehicles / num_vehicles_region) * 100
            percent_heavy = (num_heavy_vehicles / num_vehicles_region) * 100

            # Start by displaying a header and some of the summary statistics
            st.write(f"#### Summary Information for {selected_region}:")
            st.write(f"{(num_evs_region / num_vehicles_region) * 100:.2f}% of vehicles are electric, with a total of {num_evs_region} EVs")
            st.write(f"Light/Heavy Ratio for all vehicles: {percent_light:.0f}% / {percent_heavy:.0f}%")

            # Calculate the demand-to-supply ratio for each half-hour
            chart_data["Demand/Supply Ratio"] = chart_data["Demand (MWh)"] / chart_data["Supply (MWh)"]

            # Handle divide-by-zero cases (if supply is 0)
            chart_data["Demand/Supply Ratio"].replace([np.inf, -np.inf], np.nan, inplace=True)
            chart_data["Demand/Supply Ratio"].fillna(0, inplace=True)

            # Get the average ratio across the day
            avg_ratio = chart_data["Demand/Supply Ratio"].mean()

            # Calculate and display where electricity demand is closest to supply (the smallest absolute difference), and the average ratio
            chart_data["Difference"] = (chart_data["Demand (MWh)"] - chart_data["Supply (MWh)"]).abs()
            closest_time_idx = chart_data["Difference"].idxmin()
            closest_time = chart_data.loc[closest_time_idx, "Time"]
            closest_ratio = chart_data.loc[closest_time_idx, "Demand/Supply Ratio"]

            st.write(f"Average Demand/Supply Ratio: {avg_ratio:.2f}")
            st.write(f"Time of Closest Match: {closest_time} (Demand/Supply = {closest_ratio:.2f})")
