import streamlit as st
import pandas as pd
import numpy as np

# Page configuration
st.set_page_config(page_title="Vectorized Production Optimizer", layout="wide")

st.title("🏭 Production & Inventory Optimizer")
st.markdown("This version uses **vectorized calculations** for high-performance simulation.")

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("Cost Parameters")
    fixed_cost = st.number_input("Fixed Setup Cost ($)", value=5000)
    var_cost_unit = st.number_input("Variable Production Cost/Unit ($)", value=20)
    rm_cost_unit = st.number_input("Raw Material Cost/Unit ($)", value=30)
    
    st.header("Inventory Policy")
    holding_cost_pct = st.slider("Annual Holding Cost (%)", 0, 50, 15) / 100
    batch_size = st.number_input("Current Batch Size", min_value=1, value=1000)

# --- Vectorized Simulation Logic ---
# We create a range of batch sizes from 10% to 500% of the user's input
batch_sizes = np.arange(100, batch_size * 5, 100)

# Vectorized calculations using NumPy/Pandas
df = pd.DataFrame({"Batch Size": batch_sizes})

# 1. Unit Production Cost: (Fixed / Batch) + Variable
df["Unit Prod Cost"] = (fixed_cost / df["Batch Size"]) + var_cost_unit

# 2. Total Finished Good (FG) Cost: RM Cost + Unit Prod Cost
df["Unit FG Cost"] = rm_cost_unit + df["Unit Prod Cost"]

# 3. Total Inventory Investment: Batch Size * Unit FG Cost
df["Total Inventory Value"] = df["Batch Size"] * df["Unit FG Cost"]

# 4. Carrying Cost: Value * Holding Cost %
df["Annual Carrying Cost"] = df["Total Inventory Value"] * holding_cost_pct

# --- UI Display ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Cost per Unit vs. Batch Size")
    st.line_chart(df, x="Batch Size", y="Unit FG Cost")
    st.caption("Notice the 'Elbow': Costs drop sharply at first, then plateau.")

with col2:
    st.subheader("Capital Tied in Inventory")
    st.area_chart(df, x="Batch Size", y="Total Inventory Value")
    st.caption("Inventory value grows linearly, increasing your financial risk.")

# --- Summary Metrics for the Selected Batch Size ---
current_unit_cost = (fixed_cost / batch_size) + var_cost_unit + rm_cost_unit
total_inv_val = batch_size * current_unit_cost

st.divider()
m1, m2, m3 = st.columns(3)
m1.metric("Current Unit Cost", f"${current_unit_cost:.2f}")
m2.metric("Total Batch Value", f"${total_inv_val:,.2f}")
m3.metric("Raw Material Need", f"{batch_size:,.0f} units")

st.table(df.head(10)) # Showing the vectorized result table
