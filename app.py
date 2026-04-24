import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Supply Chain Auditor Pro", layout="wide")

st.title("🔗 Integrated Production & Raw Material Simulator")

# --- 1. SIDEBAR: SCENARIO SETTINGS ---
with st.sidebar:
    st.header("📈 Demand & Production")
    days = st.slider("Simulation Horizon (Days)", 100, 730, 365)
    mu = st.number_input("Average Daily Demand", value=100)
    sigma = st.number_input("Demand Variability", value=20)
    fg_batch_size = st.number_input("Production Batch Size", value=1000)
    
    st.header("🏗️ Raw Material Policy")
    rm_order_qty = st.number_input("RM Order Quantity (Q)", value=5000)
    rm_reorder_point = st.number_input("RM Reorder Point (ROP)", value=2000)
    rm_lead_time = st.slider("RM Lead Time (Days)", 0, 14, 5)
    
    st.header("💰 Cost Logic")
    fixed_setup = st.number_input("Production Setup Cost ($)", value=2000)
    rm_order_cost = st.number_input("RM Ordering Cost ($)", value=500)
    rm_unit_cost = st.number_input("RM Unit Cost ($)", value=25)
    holding_rate = st.slider("Annual Holding Rate (%)", 5, 50, 20) / 100

# --- 2. THE SIMULATION ENGINE ---
np.random.seed(42)
daily_demand = np.random.normal(mu, sigma, days).clip(min=0)

# Initialize Arrays
fg_inv = np.zeros(days)
rm_inv = np.zeros(days)
rm_on_order = np.zeros(days + rm_lead_time + 1)
prod_triggers = np.zeros(days)
rm_order_triggers = np.zeros(days)

# Initial State
curr_fg = fg_batch_size
curr_rm = rm_order_qty
curr_rm_on_order = 0

for t in range(days):
    # 1. RM Delivery: Check if any previous order arrives today
    curr_rm += rm_on_order[t]
    
    # 2. Production Check (FG)
    curr_fg -= daily_demand[t]
    if curr_fg <= 0:
        # We need a production batch. Do we have enough RM?
        if curr_rm >= fg_batch_size:
            curr_fg += fg_batch_size
            curr_rm -= fg_batch_size
            prod_triggers[t] = 1
        else:
            # STOCKOUT: Production halted due to no RM
            pass 
    
    # 3. Raw Material Reorder Check
    # Account for RM in warehouse + RM already in transit
    effective_rm = curr_rm + rm_on_order[t+1:].sum()
    if effective_rm <= rm_reorder_point:
        rm_on_order[t + rm_lead_time] += rm_order_qty
        rm_order_triggers[t] = 1
        
    fg_inv[t] = max(curr_fg, 0)
    rm_inv[t] = curr_rm

# --- 3. DATA PREP & METRICS ---
sim_df = pd.DataFrame({
    "Day": np.arange(days),
    "Daily Demand": daily_demand,
    "FG Inventory": fg_inv,
    "RM Inventory": rm_inv,
    "Prod Trigger": prod_triggers,
    "RM Order Trigger": rm_order_triggers
})

# Costing Breakup
daily_h_rate = holding_rate / 365
total_prod_fixed = prod_triggers.sum() * fixed_setup
total_rm_order_costs = rm_order_triggers.sum() * rm_order_cost
total_rm_purchase = rm_order_triggers.sum() * rm_order_qty * rm_unit_cost
total_holding = (fg_inv.mean() + rm_inv.mean()) * rm_unit_cost * daily_h_rate * days

# --- 4. VISUALIZATION ---
m1, m2, m3 = st.columns(3)
m1.metric("Total RM Orders", int(rm_order_triggers.sum()))
m2.metric("Total Production Runs", int(prod_triggers.sum()))
m3.metric("System Holding Cost", f"${total_holding:,.2f}")

st.subheader("🔄 The Multi-Stage Inventory Loop")
st.markdown("Observe how **RM orders** trigger based on the ROP to feed the **Production batches**.")
st.line_chart(sim_df.set_index("Day")[["FG Inventory", "RM Inventory"]])



st.subheader("📋 Final Cost Breakdown")
breakdown = pd.DataFrame({
    "Stream": ["Raw Material", "Raw Material", "Production", "Inventory"],
    "Type": ["Purchasing", "Ordering Costs", "Fixed Setups", "Combined Holding"],
    "Total Cost": [total_rm_purchase, total_rm_order_costs, total_prod_fixed, total_holding]
})
st.table(breakdown.style.format({"Total Cost": "${:,.2f}"}))

with st.expander("View Daily Movement Data"):
    st.dataframe(sim_df)
