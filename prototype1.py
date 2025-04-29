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
electricity_demand_ytd = helper.load_file(f"{data_dir}Zone Load Data (16 Mar - 16 Apr) [30 intervals].csv")


private_vehicles = fleet_data_2025.loc[fleet_data_2025["INDUSTRY_CLASS"] == "PRIVATE"]

electric_vehicles = fleet_data_2025.loc[fleet_data_2025["MOTIVE_POWER"] == "ELECTRIC"]

average_hourly_usage_mw = electricity_demand_ytd["NZ TOTAL(MW)"].sum() / electricity_demand_ytd["Date"].count()

average_daily_usage_gw = average_hourly_usage_mw * 24 / 1000

electric_vehicles["MAKE_MODEL"] = electric_vehicles["MAKE"] + " " + electric_vehicles["MODEL"]

most_common_ev = electric_vehicles["MAKE_MODEL"].mode()[0]

year_common_ev = electric_vehicles[electric_vehicles["MAKE_MODEL"] == most_common_ev]["VEHICLE_YEAR"].mode()[0]

st.markdown(
    """
    This prototype model displays some relevant statistics/figures from the existing data sources, and visualises a simple scenario
    in which electricity generation/supply is assumed to be 5000 MWh, whilst the electricity load/demand is calculated based on
    recent existing load data from Transpower.
    """
)

st.write(f"There are {private_vehicles.shape[0]} private vehicles registered in NZ as of 2025")

st.write(f"There are {electric_vehicles.shape[0]} battery electric vehicles registered in NZ as of 2025")

st.write(f"The average hourly usage was {round(average_hourly_usage_mw, 2)} MW")

st.write(f"The average daily usage was {round(average_daily_usage_gw, 2)} GW")

st.write(f"The most common EV is the {year_common_ev} {most_common_ev}")

print(fleet_data_2025["INDUSTRY_CLASS"].unique())

print(fleet_data_2025["MOTIVE_POWER"].unique())

if not fleet_data_2025.empty and not electricity_demand_ytd.empty:
    chart_data = pd.DataFrame({
        "Hour": list(range(24)),
        "Demand (MWh)": [average_hourly_usage_mw] * 24,
        "Supply (MWh)": [5000] * 24
    })

    st.subheader("Electricity Supply and Demand in New Zealand by Hour")

    fig = px.line(
        chart_data, 
        x="Hour", 
        y=["Demand (MWh)", "Supply (MWh)"],
        range_y=[0, chart_data[["Demand (MWh)", "Supply (MWh)"]].max().max() * 1.1]
    )

    fig.update_layout(
        xaxis_title="Hour of the Day",
        yaxis_title="Electricity Amount (MWh)"
    )

    st.plotly_chart(fig)
else:
    st.warning("Data not fully loaded yet.")
