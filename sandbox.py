"""
Python file used as a "sandbox" to test Python code without affecting the existing prototypes or other files
"""

import pandas as pd
import matplotlib as plt
import helper
import json
import streamlit as st
import streamlit_folium
import folium
import geopandas as gpd
from shapely.geometry import Point

# data_dir = "Data/"
# region_path = f"{data_dir}WGS84_GeoJSON_Zone.JSON"

# # Load the GeoJSON electricity grid regions data
# with open(region_path) as f:
#     region_gj = json.load(f)

# # Create a base map
# region_map = folium.Map(location=[-41, 174], zoom_start=6, height=700, width=700)
# folium.GeoJson(
#     region_gj,
#     tooltip=folium.GeoJsonTooltip(
#         fields=["Region"],
#         aliases=["Region"],
#         localize=True
#     )
# ).add_to(region_map)

# # Display the map in Streamlit
# result = streamlit_folium.st_folium(region_map, width=700, height=700)

# # Get the fleet data and map that shows current territorial authorities
# fleet_df_2025 = helper.load_file(f"{data_dir}Fleet-31Mar2025.csv")
# ta_path =  f"{data_dir}territorial-authority-2025.json"
# ta_gdf = gpd.read_file(ta_path)
# region_gdf = gpd.read_file(region_path)

# # Prepare the data, including converting to the same CRS and ensuring that the geometry is valid
# ta_gdf = ta_gdf.to_crs(epsg=4326)
# region_gdf = region_gdf.to_crs(epsg=4326)
# region_gdf["geometry"] = region_gdf.buffer(0)

# # Spatial join the territorial authority and region data
# ta_with_regions = gpd.sjoin(ta_gdf, region_gdf, how="left", predicate="intersects")

# # Map the territorial authorities to the right regions, including handling uppercase words
# ta_region_map = dict(zip(ta_with_regions["TA2025_V_2"], ta_with_regions["Region"]))
# ta_region_map = {
#     k.upper(): v.upper()
#     for k, v in ta_region_map.items()
# }
# fleet_df_2025["REGION"] = fleet_df_2025["TLA"].map(ta_region_map)

# print(fleet_df_2025.head())

# # Handle interactivity on the map
# matched_region = None
# if result["last_clicked"] is not None:
#     clicked_point = Point(result["last_clicked"]["lng"], result["last_clicked"]["lat"])
#     match = region_gdf[region_gdf.geometry.contains(clicked_point)]
    
#     if not match.empty:
#         matched_region = match["Region"].iloc[0]

# # Show the number of electric vehicles present in the currently selected region
# if matched_region is not None:
#     num_evs_region = ((fleet_df_2025["MOTIVE_POWER"] == "ELECTRIC") & (fleet_df_2025["REGION"] == matched_region.upper())).sum()
#     st.write(f"There are {num_evs_region} electric vehicles in {matched_region}")