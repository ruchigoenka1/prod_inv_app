import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Production & Inventory Optimizer", layout="wide")

st.title("🏭 Total Cost of Production & Inventory Simulator")

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("⏱️ Simulation Settings")
    days = st.slider("Simulation Horizon (Days)", 100, 730, 365)
    
    st.header("📈 Demand (Normal Distribution)")
    mu = st.number_input("Mean Daily Demand", value=50)
    sigma = st.number_input("Daily Demand Variability (Std Dev)", value=10)
    
    st.header("💰 Cost Factors")
    fixed_setup = st.number_input("Fixed Cost per Batch ($)", value=2000)
    var_prod_unit = st.number_input("Variable Production/Unit ($)", value=15)
    rm_cost_unit = st.number_input("Raw Material/Unit ($)", value=25)
    
    st.header("📦 Inventory Policy")
    batch_size = st.number_input("Chosen Batch Size", min_value=1, value=500)
    holding_rate_annual = st.slider("Annual Holding Cost %", 5, 50, 20) / 100

# --- VECTORIZED CALCULATIONS ---
# 1. Daily Demand Simulation
np.random.seed(42)
daily_demand = np.random.normal(mu, sigma, days).clip(min=0)
total_demand = daily_demand.sum()

# 2. Production Metrics
num_batches = np.ceil(total_demand / batch_size)
total_units = num_batches * batch_size
daily_holding_rate = holding_rate_annual / 365

# 3. Cost Breakup Logic
# Raw Material
rm_purchase = total_units * rm_cost_unit
rm_holding = (batch_size / 2) * rm_cost_unit * daily_holding_rate * days

# Production
prod_fixed = num_batches * fixed_setup
prod_variable = total_units * var_prod_unit

# Finished Goods (FG)
unit_fg_val = rm_cost_unit + var_prod_unit + (prod_fixed / total_units)
fg_holding = (batch_size / 2) * unit_fg_val * daily_holding_rate * days

total_cost = rm_purchase + rm_holding + prod_fixed + prod_variable + fg_holding

# --- UI: DISPLAY METRICS & TABLE ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total TCO", f"${total_cost:,.2f}")
col2.metric("Batches Run", int(num_batches))
col3.metric("Avg. Unit Cost", f"${(total_cost/total_units):.2f}")
col4.metric("Total Production", f"{total_units:,.0f} units")

st.subheader("📋 Total Cost Breakup")
breakdown_data = {
    "Category": ["Raw Material", "Raw Material", "Production", "Production", "Finished Goods", "TOTAL"],
    "Cost Component": ["Purchase/Ordering", "Holding Cost", "Fixed (Setup)", "Variable (Volume)", "Holding Cost", "All In"],
    "Amount ($)": [rm_purchase, rm_holding, prod_fixed, prod_variable, fg_holding, total_cost]
}
st.table(pd.DataFrame(breakdown_data).style.format({"Amount ($)": "{:,.2f}"}))

# --- VECTORIZED SENSITIVITY ANALYSIS ---
st.divider()
st.subheader("📉 Optimization: Finding the 'Sweet Spot'")
st.markdown("This chart shows how **Total Cost** changes as you adjust the Batch Size.")

# Vectorized array for batch sizes 100 to 5000
b_range = np.arange(100, 5001, 50)
s_batches = np.ceil(total_demand / b_range)

# Vectorized Costing
s_fixed = s_batches * fixed_setup
s_holding = (b_range / 2) * (rm_cost_unit + var_prod_unit) * daily_holding_rate * days
s_total = (total_demand * (rm_cost_unit + var_prod_unit)) + s_fixed + s_holding

viz_df = pd.DataFrame({
    "Batch Size": b_range,
    "Setup Costs": s_fixed,
    "Inventory Holding Costs": s_holding,
    "Total System Cost": s_total
}).set_index("Batch Size")

st.line_chart(viz_df)

st.success(f"**Insight:** To minimize costs over {days} days, your batch size should be near the lowest point of the 'Total System Cost' curve.")
