"""
Python file that contains helper code/functions for the project code
"""

# Import the necessary libraries/packages
import pandas as pd
import streamlit as st

# Stops unnecessary refreshes
@st.cache_data
def load_file(path): 
    """
    Function that loads in a CSV file as a Pandas dataframe

    path: Path to the file to be read in

    Returns: A dataframe containing the data from the file
    """

    df = pd.read_csv(path)

    return df
