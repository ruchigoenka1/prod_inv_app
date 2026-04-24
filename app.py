import streamlit as st
import pandas as pd
import numpy as np

# 1. PAGE SETUP (Must be the first Streamlit command)
st.set_page_config(page_title="Supply Chain Auditor Pro", layout="wide")

st.title("🏭 Ultimate Supply Chain & Production Auditor")
st.markdown("---")

# 2. SIDEBAR: PROFESSIONAL PARAMETERS
with st.sidebar:
    st.header("⏱️ Simulation Horizon")
    days = st.slider("Timeline (Days)", 100, 730, 365)
    
    st.header("📈 Demand Profile")
    mu = st.number_input("Average Daily Demand", value=100)
    sigma = st.number_input("Demand Variability (Std Dev)", value=25)
    
    st.header("🏗️ Raw Material (RM) Policy")
    rm_order_qty = st.number_input("RM Order Quantity (Q)", value=5000)
    rm_rop = st.number_input("RM Reorder Point (ROP)", value=2500)
    rm_lead_time = st.slider("RM Lead Time (Days)", 1, 14, 5)
    rm_unit_cost = st.number_input("RM Cost per Unit ($)", value=25)
    rm_order_fixed_cost = st.number_input("Fixed Cost per RM Order ($)", value=300)
    rm_hold_rate = st.slider("RM Annual Holding Rate (%)", 5, 50, 15) / 100
    
    st.header("📦 Production (FG) Policy")
    fg_batch_size = st.number_input("Production Batch Size", value=1500)
    fg_trigger_level = st.number_input("Production Trigger (FG ROP)", value=800)
    prod_lead_time = st.slider("Production Lead Time (Days)", 1, 14, 3)
    fg_fixed_setup = st.number_input("Setup Cost per Batch ($)", value=2000)
    fg_var_cost = st.number_input("Variable Prod Cost/Unit ($)", value=15)
    fg_hold_rate = st.slider("FG Annual Holding Rate (%)", 5, 50, 25) / 100

# 3. VECTORIZED SIMULATION ENGINE
np.random.seed(42)
daily_demand = np.random.normal(mu, sigma, days).clip(min=0)

# Arrays for state tracking
fg_inv = np.zeros(days)
rm_inv = np.zeros(days)
rm_on_order = np.zeros(days + rm_lead_time + 1)
fg_in_production = np.zeros(days + prod_lead_time + 1)
prod_triggers = np.zeros(days)
rm_order_triggers = np.zeros(days)
unmet_demand = np.zeros(days)
stockout_flag = np.zeros(days)

# Initial conditions
curr_fg = fg_batch_size
curr_rm = rm_order_qty

for t in range(days):
    # A. Incoming Logistics
    curr_rm += rm_on_order[t]
    curr_fg += fg_in_production[t]
    
    # B. Daily Demand & Stockout Tracking
    demand = daily_demand[t]
    if curr_fg >= demand:
        curr_fg -= demand
    else:
        unmet_demand[t] = demand - curr_fg
        stockout_flag[t] = 1
        curr_fg = 0
    
    # C. Production Trigger (FG ROP Logic)
    pipeline_fg = fg_in_production[t+1:].sum()
    if (curr_fg + pipeline_fg) <= fg_trigger_level:
        # Check if RM is available to start the batch
        if curr_rm >= fg_batch_size:
            fg_in_production[t + prod_lead_time] += fg_batch_size
            curr_rm -= fg_batch_size
            prod_triggers[t] = 1

    # D. RM Reorder Trigger (RM ROP Logic)
    pipeline_rm = rm_on_order[t+1:].sum()
    if (curr_rm + pipeline_rm) <= rm_rop:
        rm_on_order[t + rm_lead_time] += rm_order_qty
        rm_order_triggers[t] = 1
        
    fg_inv[t] = curr_fg
    rm_inv[t] = curr_rm

# 4. AUDIT & COST CALCULATIONS
total_demand = np.sum(daily_demand)
fill_rate = ((total_demand - np.sum(unmet_demand)) / total_demand) * 100
daily_rm_h_rate = rm_hold_rate / 365
daily_fg_h_rate = fg_hold_rate / 365

# Cost Bifurcation
num_rm_orders = rm_order_triggers.sum()
cost_rm_purchase = (num_rm_orders * rm_order_qty) * rm_unit_cost
cost_rm_ordering = num_rm_orders * rm_order_fixed_cost
cost_rm_holding = np.sum(rm_inv * rm_unit_cost * daily_rm_h_rate)

cost_prod_fixed = prod_triggers.sum() * fg_fixed_setup
cost_prod_var = (prod_triggers.sum() * fg_batch_size) * fg_var_cost

# Finished Goods Holding (Unit Value = RM + Var Cost)
cost_fg_holding = np.sum(fg_inv * (rm_unit_cost + fg_var_cost) * daily_fg_h_rate)

total_tco = (cost_rm_purchase + cost_rm_ordering + cost_rm_holding + 
             cost_prod_fixed + cost_prod_var + cost_fg_holding)

# 5. DASHBOARD UI
m1, m2, m3, m4 = st.columns(4)
m1.metric("Service Fill Rate", f"{fill_rate:.1f}%", delta=f"{int(stockout_flag.sum())} Stockout Days", delta_color="inverse")
m2.metric("System TCO", f"${total_tco:,.0f}")
m3.metric("Prod Runs", int(prod_triggers.sum()))
m4.metric("Avg RM Stock", f"{rm_inv.mean():,.0f}")

st.subheader("📋 Granular Cost Audit")
breakdown_df = pd.DataFrame({
    "Category": ["Raw Material", "Raw Material", "Raw Material", "Production", "Production", "Finished Goods", "TOTAL"],
    "Component": ["Purchase Cost", "Ordering/PO Cost", "Holding Cost (RM)", "Setup Cost", "Variable Cost", "Holding Cost (FG)", "TCO"],
    "Amount ($)": [cost_rm_purchase, cost_rm_ordering, cost_rm_holding, cost_prod_fixed, cost_prod_var, cost_fg_holding, total_tco]
})
st.table(breakdown_df.style.format({"Amount ($)": "{:,.2f}"}))

st.divider()

# 6. VISUALIZATION
st.subheader("📉 The Inventory 'Sawtooth' & Supply Gaps")
viz_df = pd.DataFrame({
    "Day": range(days),
    "RM Inventory": rm_inv,
    "FG Inventory": fg_inv,
    "STOCKOUT": stockout_flag * (max(rm_inv.max(), fg_inv.max()))
}).set_index("Day")

st.line_chart(viz_df, color=["#29b5e8", "#ffaa00", "#ff0000"])
st.bar_chart(daily_demand)

st.info(f"**Auditor Insight:** The red vertical lines show exactly when you failed to meet demand. If they appear while FG is above 0, it means the current demand exceeded your safety stock.")
