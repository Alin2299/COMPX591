"""
Python file for Prototype 2 of the model that allows users to simulate the effects of increased EV uptake
on electricity demand in New Zealand, based on selected charging behaviour.
"""

import streamlit as st
import altair as alt
import pandas as pd
import plotly.express as px
import helper

st.title("Interactive Electricity Grid Model - Prototype 2")

# Load data
data_dir = "Data/"
fleet_data = helper.load_file(f"{data_dir}Fleet-31Mar2025.csv")
load_data = helper.load_file(f"{data_dir}Zone Load Data (16 Mar - 16 Apr) [30 intervals].csv")

# Calculate average hourly demand from real data
average_hourly_demand = load_data["NZ TOTAL(MW)"].sum() / load_data["Date"].count()

st.markdown("""
Use the sliders below to simulate how increased EV uptake and charging patterns
might affect electricity demand across a 24-hour period in New Zealand.
""")

# User inputs
ev_uptake_percent = st.slider("Projected EV Uptake by 2030 (%)", 0, 100, 50)
charging_pattern = st.selectbox("Preferred EV Charging Time", [
    "Evening (6-9pm)", "Overnight (12-6am)", "Spread Throughout Day"
])

# Estimate extra demand (simple mock multiplier)
extra_demand_per_percent = 20  # Arbitrary number for demo purposes
extra_demand_total = ev_uptake_percent * extra_demand_per_percent  # MWh total

# Distribute extra demand over hours based on charging pattern
hourly_demand = []
for hour in range(24):
    base = average_hourly_demand
    extra = 0

    if charging_pattern == "Evening (6-9pm)" and 18 <= hour <= 20:
        extra = extra_demand_total / 3
    elif charging_pattern == "Overnight (12-6am)" and 0 <= hour <= 5:
        extra = extra_demand_total / 6
    elif charging_pattern == "Spread Throughout Day":
        extra = extra_demand_total / 24

    hourly_demand.append(base + extra)

# Create DataFrame
df = pd.DataFrame({
    "Hour": list(range(24)),
    "Simulated Demand (MWh)": hourly_demand,
    "Supply (MWh)": [5000] * 24  # Constant assumed supply
})

df_long = df.melt(id_vars="Hour", var_name="Type", value_name="MWh")

chart = alt.Chart(df_long).mark_line().encode(
    x='Hour:Q',
    y='MWh:Q',
    color='Type:N'
).properties(
    width=700,
    height=400,
    title='Simulated Demand vs Supply'
)

st.altair_chart(chart, use_container_width=True)