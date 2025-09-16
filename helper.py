"""
Python file that contains helper code/functions for the project code; in particular, functions that help implement Streamlit caching properly

Note the use of caching with some of the functions to help optimise performance
"""

# Import the necessary libraries/packages
import pandas as pd
import streamlit as st
import geopandas as gpd

@st.cache_resource
def load_file(path, num_skip_rows=0): 
    """
    Function that loads in a CSV file as a Pandas dataframe

    path: Path to the file to be read in

    Returns: A dataframe containing the data from the file
    """
    df = pd.read_csv(path, skiprows=num_skip_rows)

    return df


def get_electric_mask(df):
    """
    Function that returns a mask for filtering out electric vs non-electric powered vehicles in the fleet dataframes

    df: Dataframe to be processed

    Returns: The appropriate mask
    """
    electric_mask = (df["MOTIVE_POWER"].isin(["ELECTRIC", "ELECTRIC [PETROL EXTENDED]", "ELECTRIC FUEL CELL HYDROGEN"])) | (df["MOTIVE_POWER"].str.contains("PLUGIN", na=False))
    return electric_mask

@st.cache_resource
def get_cleaned_fleet_df(fleet_path, ta_region_map):
    """
    Function that processes and maps the fleet dataframe to the regions so that caching works as expected 

    fleet_path: The filepath to the fleet data file
    ta_region_map: The GeoJSON file showing the territorial authorities in New Zealand

    Returns: The processed dataframe

    """

    # Load and apply  mapping
    raw_df = load_file(fleet_path)
    raw_df["REGION"] = raw_df["TLA"].map(ta_region_map)

    # Remove invalid and ambiguous fleet data
    raw_df = raw_df[raw_df["REGION"].notna()].copy()
    raw_df = raw_df[raw_df["MOTIVE_POWER"] != "OTHER"]

    return raw_df

@st.cache_resource
def build_region_fleet_summary(fleet_df):
    """
    Function that creates a summary dataframe of the New Zealand fleet composition and information, by region, for use in scenarios and interactivity

    fleet_df: The dataframe describing the fleet

    Returns: A dataframe representing the summarised information
    """
    # Get the list of regions that the vehicles could be associated with from the dataframe
    vehicle_regions = fleet_df["REGION"].unique()

    # For each region, create a row that contains information about the size and characteristics/composition of the vehicles in that region
    rows_list = []

    for region in vehicle_regions:
        filtered_fleet_df = fleet_df[fleet_df["REGION"] == region]

        # Filter to get different relevant values such as the number of total electric vehicles in the given region
        electric_mask = get_electric_mask(filtered_fleet_df)
        num_light_electric_vehicles = filtered_fleet_df[(electric_mask) & (filtered_fleet_df["GROSS_VEHICLE_MASS"] <= 3500)].shape[0]
        num_heavy_electric_vehicles = filtered_fleet_df[(electric_mask) & (filtered_fleet_df["GROSS_VEHICLE_MASS"] > 3500)].shape[0]

        num_light_combustion_vehicles = filtered_fleet_df[(~electric_mask) & (filtered_fleet_df["GROSS_VEHICLE_MASS"] <= 3500)].shape[0]
        num_heavy_combustion_vehicles = filtered_fleet_df[(~electric_mask) & (filtered_fleet_df["GROSS_VEHICLE_MASS"] > 3500)].shape[0]

        # Add to the appropriate temporary list
        rows_list.append({
            "Region": region,
            "Light Electric Vehicle Count": num_light_electric_vehicles,
            "Heavy Electric Vehicle Count": num_heavy_electric_vehicles,
            "Light Combustion Vehicle Count": num_light_combustion_vehicles,
            "Heavy Combustion Vehicle Count": num_heavy_combustion_vehicles
        })
    summary_df = pd.DataFrame(rows_list).set_index("Region")
    totals_row = summary_df.sum()

    summary_df.loc["NEW ZEALAND"] = totals_row

    return summary_df

@st.cache_resource
def get_avg_profiles(day_index, supply_df, demand_df):
    """
    Function that calculates the average supply and demand profile for a given region and weekday index

    day_index: The array index that corresponds to the user-selected day of the week to be profiled
    supply_df: The processed electricity supply dataframe
    demand_df: The processed electricity demand dataframe

    Returns: The average electricity supply and demand profiles
    """
    supply_df["Trading_Date"] = pd.to_datetime(supply_df["Trading_Date"])
    demand_df["Trading_Date"] = pd.to_datetime(demand_df["Trading_Date"])

    supply_avg = supply_df[supply_df["Trading_Date"].dt.dayofweek == day_index].select_dtypes(include="number").mean(axis=0)
    demand_avg = demand_df[demand_df["Trading_Date"].dt.dayofweek == day_index].select_dtypes(include="number").mean(axis=0)

    return demand_avg, supply_avg


@st.cache_resource
def get_ta_region_map(ta_path, _region_gdf):
    """
    Function that maps NZ territorial authorities to the given region data

    ta_path: The file path to the territorial authority mapping data
    region_path: The file path to the regions mapping data

    Returns: A processed dictionary representing the final joined data/mapping
    """
    ta_gdf = gpd.read_file(ta_path).to_crs(epsg=4326)
    region_gdf = _region_gdf.to_crs(epsg=4326)
    region_gdf["geometry"] = region_gdf.buffer(0)

    ta_with_regions = gpd.sjoin(ta_gdf, region_gdf, how="left", predicate="intersects")

    # Handle uppercase words
    ta_region_map = dict(zip(ta_with_regions["TA2025_V_2"], ta_with_regions["Region"]))
    return {k.upper(): v.upper() for k, v in ta_region_map.items()}

