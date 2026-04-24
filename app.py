import streamlit as st
import pandas as pd
import numpy as np

# Page Configuration
st.set_page_config(page_title="Supply Chain Auditor Pro", layout="wide")

st.title("🏭 Total Cost Auditor: Production & Supply Chain")
st.markdown("---")

# --- 1. SIDEBAR: PROFESSIONAL PARAMETERS ---
with st.sidebar:
    st.header("⏱️ Simulation Period")
    days = st.slider("Time Horizon (Days)", 100, 730, 365)
    
    st.header("📈 Demand & Risk")
    mu = st.number_input("Average Daily Demand", value=100)
    sigma = st.number_input("Demand Variability (Std Dev)", value=25)
    
    st.header("🏗️ Raw Material (RM) Policy")
    rm_order_qty = st.number_input("RM Order Quantity (Q)", value=5000)
    rm_rop = st.number_input("RM Reorder Point (ROP)", value=2000)
    rm_lead_time = st.slider("RM Lead Time (Days)", 0, 14, 5)
    rm_unit_cost = st.number_input("RM Cost per Unit ($)", value=25)
    rm_order_fixed_cost = st.number_input("Fixed Cost per RM Order ($)", value=300)
    rm_hold_rate = st.slider("RM Annual Holding Rate (%)", 5, 50, 15) / 100
    
    st.header("📦 Production (FG) Policy")
    fg_batch_size = st.number_input("Production Batch Size", value=1000)
    fg_fixed_setup = st.number_input("Setup Cost per Batch ($)", value=2000)
    fg_var_cost = st.number_input("Variable Prod Cost/Unit ($)", value=15)
    fg_hold_rate = st.slider("FG Annual Holding Rate (%)", 5, 50, 25) / 100

# --- 2. THE SIMULATION ENGINE ---
np.random.seed(42)
daily_demand = np.random.normal(mu, sigma, days).clip(min=0)

# Vectors for state tracking
fg_inv = np.zeros(days)
rm_inv = np.zeros(days)
rm_on_order = np.zeros(days + rm_lead_time + 1)
prod_triggers = np.zeros(days)
rm_order_triggers = np.zeros(days)

# Initial conditions
curr_fg = fg_batch_size
curr_rm = rm_order_qty

for t in range(days):
    # A. RM Delivery Check
    curr_rm += rm_on_order[t]
    
    # B. Finished Goods Consumption
    curr_fg -= daily_demand[t]
    
    # C. Production Trigger
    if curr_fg <= 0:
        if curr_rm >= fg_batch_size:
            curr_fg += fg_batch_size
            curr_rm -= fg_batch_size
            prod_triggers[t] = 1

    # D. RM Reorder Trigger (Inventory + Transit)
    effective_rm = curr_rm + rm_on_order[t+1:].sum()
    if effective_rm <= rm_rop:
        rm_on_order[t + rm_lead_time] += rm_order_qty
        rm_order_triggers[t] = 1
        
    fg_inv[t] = max(curr_fg, 0)
    rm_inv[t] = curr_rm

# --- 3. VECTORIZED BIFURCATED COST ANALYSIS ---
daily_rm_h_rate = rm_hold_rate / 365
daily_fg_h_rate = fg_hold_rate / 365

# Raw Material Costs (BIFURCATED)
num_rm_orders = rm_order_triggers.sum()
cost_rm_purchase = (num_rm_orders * rm_order_qty) * rm_unit_cost
cost_rm_ordering = num_rm_orders * rm_order_fixed_cost
cost_rm_holding = np.sum(rm_inv * rm_unit_cost * daily_rm_h_rate)

# Production Costs
total_batches = prod_triggers.sum()
cost_prod_fixed = total_batches * fg_fixed_setup
cost_prod_var = (total_batches * fg_batch_size) * fg_var_cost

# Finished Goods Holding Costs
unit_fg_value = rm_unit_cost + fg_var_cost
cost_fg_holding = np.sum(fg_inv * unit_fg_value * daily_fg_h_rate)

total_tco = (cost_rm_purchase + cost_rm_ordering + cost_rm_holding + 
             cost_prod_fixed + cost_prod_var + cost_fg_holding)

# --- 4. DASHBOARD UI ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total System TCO", f"${total_tco:,.2f}")
m2.metric("Production Runs", int(total_batches))
m3.metric("Purchase Orders (PO)", int(num_rm_orders))
m4.metric("Avg RM Stock", f"{rm_inv.mean():,.0f}")

st.subheader("📋 Granular Cost Breakup")
breakdown_df = pd.DataFrame({
    "Category": ["Raw Material", "Raw Material", "Raw Material", "Production", "Production", "Finished Goods", "TOTAL"],
    "Component": ["Material Purchase Cost", "Ordering/Fixed PO Cost", "Holding Cost (RM)", 
                  "Fixed Setup Cost", "Variable Volume Cost", "Holding Cost (FG)", "System TCO"],
    "Value ($)": [cost_rm_purchase, cost_rm_ordering, cost_rm_holding, 
                  cost_prod_fixed, cost_prod_var, cost_fg_holding, total_tco]
})
st.table(breakdown_df.style.format({"Value ($)": "{:,.2f}"}))

st.divider()

# --- 5. VISUALIZATIONS ---
st.subheader("📉 Movement & Demand Visualization")
viz_df = pd.DataFrame({
    "Day": range(days),
    "RM Inventory": rm_inv,
    "FG Inventory": fg_inv,
    "Daily Demand": daily_demand
}).set_index("Day")

st.line_chart(viz_df[["RM Inventory", "FG Inventory"]])
st.bar_chart(viz_df["Daily Demand"])

st.info("💡 **Auditor Note:** Notice how bifurcating RM costs reveals that even if your Purchase Cost is high, your 'Ordering Cost' is actually a choice of frequency vs. volume.")
