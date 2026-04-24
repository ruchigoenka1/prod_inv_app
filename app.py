import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Pro Inventory Auditor", layout="wide")

st.title("🏭 Professional Production & Inventory Simulator")

# --- 1. SIDEBAR: PROFESSIONAL PARAMETERS ---
with st.sidebar:
    st.header("⏱️ Simulation Period")
    days = st.slider("Time Horizon (Days)", 100, 730, 365)
    
    st.header("📈 Demand & Risk")
    mu = st.number_input("Average Daily Demand", value=100)
    sigma = st.number_input("Demand Variability (Std Dev)", value=25)
    safety_stock = st.number_input("Safety Stock Level", value=200)
    
    st.header("💰 Cost Architecture")
    fixed_setup = st.number_input("Setup/Fixed Cost ($)", value=5000)
    # Variable cost logic: we'll simulate it decreasing slightly with volume
    base_var_cost = st.number_input("Base Variable Cost/Unit ($)", value=20)
    rm_cost_unit = st.number_input("Raw Material Cost/Unit ($)", value=35)
    
    st.header("📦 Batching Policy")
    batch_size = st.number_input("Production Batch Size", min_value=1, value=1000)
    annual_holding_rate = st.slider("Annual Holding Cost (%)", 5, 50, 20) / 100

# --- 2. VECTORIZED ENGINE ---
# Generate Demand
np.random.seed(42)
days_array = np.arange(days)
daily_demand = np.random.normal(mu, sigma, days).clip(min=0)
cumulative_demand = np.cumsum(daily_demand)

# Vectorized Batch Calculation
# We calculate when 'cumulative demand + safety stock' exceeds our available supply
total_needed = cumulative_demand + safety_stock
batches_needed = np.ceil(total_needed / batch_size).astype(int)

# Identify specifically where a batch "Spikes"
# A batch is triggered when the number of needed batches increases from the previous day
batch_triggers = np.diff(batches_needed, prepend=0) 
production_spikes = batch_triggers * batch_size

# Calculate Inventories (Vectorized)
# FG Inventory = (Total Batches Produced to date) - (Cumulative Demand to date)
fg_inventory = (np.cumsum(batch_triggers) * batch_size) - cumulative_demand

# RM Inventory = (Total RM purchased initially) - (Total used in production so far)
total_rm_required = np.sum(batch_triggers) * batch_size
rm_inventory = total_rm_required - (np.cumsum(batch_triggers) * batch_size)

# --- 3. COST BREAKDOWN TABLE ---
# Calculate components
num_batches = batch_triggers.sum()
total_units = num_batches * batch_size
daily_holding_rate = annual_holding_rate / 365

cost_rm_purchase = total_units * rm_cost_unit
cost_rm_holding = np.mean(rm_inventory) * rm_cost_unit * daily_holding_rate * days
cost_prod_fixed = num_batches * fixed_setup
cost_prod_var = total_units * base_var_cost
# Finished Good Value = (RM + Var + Fixed Spread)
unit_fg_value = rm_cost_unit + base_var_cost + (cost_prod_fixed / total_units if total_units > 0 else 0)
cost_fg_holding = np.mean(fg_inventory) * unit_fg_value * daily_holding_rate * days

total_tco = cost_rm_purchase + cost_rm_holding + cost_prod_fixed + cost_prod_var + cost_fg_holding

# --- 4. UI DISPLAY ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total TCO", f"${total_tco:,.2f}")
m2.metric("Total Units", f"{total_units:,.0f}")
m3.metric("Avg. Holding Cost/Day", f"${(cost_rm_holding + cost_fg_holding)/days:,.2f}")
m4.metric("Batches Required", int(num_batches))

st.subheader("📊 Inventory Movement & Demand")
tab1, tab2 = st.tabs(["Visual Movement", "Detailed Data"])

with tab1:
    # Prepare DataFrame for plotting
    plot_df = pd.DataFrame({
        "Day": days_array,
        "Daily Demand": daily_demand,
        "FG Inventory": fg_inventory,
        "RM Inventory": rm_inventory
    }).set_index("Day")
    
    st.line_chart(plot_df[["FG Inventory", "RM Inventory"]])
    st.bar_chart(plot_df["Daily Demand"])

with tab2:
    st.dataframe(plot_df, use_container_width=True)

st.subheader("📝 Cost Breakup Table")
breakdown_df = pd.DataFrame({
    "Major Category": ["Raw Material", "Raw Material", "Production", "Production", "Finished Goods", "TOTAL"],
    "Line Item": ["Purchasing", "Holding Cost", "Fixed Setup", "Variable Volume", "Holding Cost", "System Total"],
    "Amount ($)": [cost_rm_purchase, cost_rm_holding, cost_prod_fixed, cost_prod_var, cost_fg_holding, total_tco]
})
st.table(breakdown_df.style.format({"Amount ($)": "{:,.2f}"}))
