"""
Python file for Prototype 1 of the model, which will be able to load in and process data to show some basic visualisations of electricity demand and supply
"""

# Import the necessary libraries/packages
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import time
import helper 
import plotly.express as px

st.title("Interactive Electricity Grid Model - Prototype 1")

data_dir = "Data/"

fleet_data_2025 = helper.load_file(f"{data_dir}Fleet-31Mar2025.csv")
electricity_demand_ytd = helper.load_file(f"{data_dir}Zone Data (16 Mar - 16 Apr) [30 intervals].csv")


private_vehicles = fleet_data_2025.loc[fleet_data_2025["INDUSTRY_CLASS"] == "PRIVATE"]

electric_vehicles = fleet_data_2025.loc[fleet_data_2025["MOTIVE_POWER"] == "ELECTRIC"]

average_hourly_usage_mw = electricity_demand_ytd["NZ TOTAL(MW)"].sum() / electricity_demand_ytd["Date"].count()

average_daily_usage_gw = average_hourly_usage_mw * 24 / 1000

st.write(f"There are {private_vehicles.shape[0]} private vehicles registered in NZ as of 2025")

st.write(f"There are {electric_vehicles.shape[0]} battery electric vehicles registered in NZ as of 2025")

st.write(f"The average hourly usage was {round(average_hourly_usage_mw, 2)} MW")

st.write(f"The average daily usage was {round(average_daily_usage_gw, 2)} GW")

st.write(fleet_data_2025["INDUSTRY_CLASS"].unique())

st.write(fleet_data_2025["MOTIVE_POWER"].unique())


chart_data = pd.DataFrame({
    "Hour": list(range(24)),
    "Demand (MWh)": [average_hourly_usage_mw] * 24,
    "Supply (MWh)": [5000] * 24
})

st.subheader("Electricity Supply and Demand in New Zealand by Hour")

# Create Plotly line chart
fig = px.line(chart_data, x="Hour", y=["Demand (MWh)", "Supply (MWh)"])

# Custom X-axis label
fig.update_layout(
    xaxis_title="Hour of the Day",  # This sets the custom X-axis label
    yaxis_title="Electricity Amount (MWh)"  # Optional: custom Y-axis label
)

# Display in Streamlit
st.plotly_chart(fig)

# # Initialize the counter in session state if not already set
# if "counter" not in st.session_state:
#     st.session_state.counter = 0

# # Button that increases the counter
# if st.button("Increase"):
#     st.session_state.counter += 1

# # Show the current value
# st.write(f"Counter value: {st.session_state.counter}")