"""
Python file for Prototype 2 of the model that allows users to simulate the effects of increased EV uptake
on electricity demand in New Zealand, based on selected charging behaviour.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import helper

st.title("Interactive Electricity Grid Model - Prototype 2")

# Load all data
data_dir = "Data/"
fleet_df = helper.load_file(f"{data_dir}Fleet-31Mar2025.csv")
march_demand_df = helper.load_file(f"{data_dir}Demand_trends_202503.csv", 11)
march_generation_df = helper.load_file(f"{data_dir}202503_Generation_MD.csv")

# Process/prepare the dataframe
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

# Create a plot of the electricity demand vs supply
chart_data = pd.DataFrame({
    "Trading Period": list(range(1, 49)),
    "Demand (MWh)": demand_values,
    "Supply (MWh)": supply_values
})

st.subheader("Electricity Supply and Demand in New Zealand by Time")

fig = px.line(
    chart_data, 
    x="Trading Period", 
    y=["Demand (MWh)", "Supply (MWh)"],
    range_y=[0, chart_data[["Demand (MWh)", "Supply (MWh)"]].max().max() * 1.1]
)

fig.update_layout(
    xaxis_title="Trading Period",
    yaxis_title="Electricity Amount (MWh)"
)

st.plotly_chart(fig)
