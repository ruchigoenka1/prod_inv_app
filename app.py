import streamlit as st
import pandas as pd
import numpy as np

# Page Configuration
st.set_config(page_title="Supply Chain Auditor Pro", layout="wide")

st.title("🏭 Professional Inventory & Production Auditor")
st.markdown("---")

# --- 1. SIDEBAR: PROFESSIONAL PARAMETERS ---
with st.sidebar:
    st.header("⏱️ Simulation Settings")
    days = st.slider("Timeline (Days)", 100, 730, 365)
    
    st.header("📈 Demand & Risk")
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
    fg_trigger_level = st.number_input("Production Reorder Point (FG ROP)", value=800)
    prod_lead_time = st.slider("Production Lead Time (Days)", 1, 14, 3)
    fg_fixed_setup = st.number_input("Setup Cost per Batch ($)", value=2000)
    fg_var_cost = st.number_input("Variable Prod Cost/Unit ($)", value=15)
    fg_hold_rate = st.slider("FG Annual Holding Rate (%)", 5, 50, 25) / 100

# --- 2. THE VECTORIZED SIMULATION ENGINE ---
np.random.seed(42)
daily_demand = np.random.normal(mu, sigma, days).clip(min=0)

# Vectors for state tracking
fg_inv = np.zeros(days)
rm_inv = np.zeros(days)
rm_on_order = np.zeros(days + rm_lead_time + 1)
fg_in_production = np.zeros(days + prod_lead_time + 1)
prod_triggers = np.zeros(days)
rm_order_triggers = np.zeros(days)
unmet_demand = np.zeros(days)

# Initial conditions
curr_fg = fg_batch_size
curr_rm = rm_order_qty

for t in range(days):
    # A. Incoming Arrivals (RM and FG)
    curr_rm += rm_on_order[t]
    curr_fg += fg_in_production[t]
    
    # B. Daily Demand & Stockout Check
    demand = daily_demand[t]
    if curr_fg >= demand:
        curr_fg -= demand
    else:
        unmet_demand[t] = demand - curr_fg
        curr_fg = 0
    
    # C. Production Trigger (FG ROP)
    # Check current FG + what is already in the production pipeline
    pipeline_fg = fg_in_production[t+1:].sum()
    if (curr_fg + pipeline_fg) <= fg_trigger_level:
        if curr_rm >= fg_batch_size:
            fg_in_production[t + prod_lead_time] += fg_batch_size
            curr_rm -= fg_batch_size
            prod_triggers[t] = 1

    # D. Raw Material Reorder Trigger
    pipeline_rm = rm_on_order[t+1:].sum()
    if (curr_rm + pipeline_rm) <= rm_rop:
        rm_on_order[t + rm_lead_time] += rm_order_qty
        rm_order_triggers[t] = 1
        
    fg_inv[t] = curr_fg
    rm_inv[t] = curr_rm

# --- 3. AUDIT CALCULATIONS ---
stockout_days = np.sum(unmet_demand > 0)
total_demand = np.sum(daily_demand)
fill_rate = ((total_demand - np.sum(unmet_demand)) / total_demand) * 100

# Costing Breakup
daily_rm_h_rate = rm_hold_rate / 365
daily_fg_h_rate = fg_hold_rate / 365

cost_rm_purchase = (rm_order_triggers.sum() * rm_order_qty) * rm_unit_cost
cost_rm_ordering = rm_order_triggers.sum() * rm_order_fixed_cost
cost_rm_holding = np.sum(rm_inv * rm_unit_cost * daily_rm_h_rate)

cost_prod_fixed = prod_triggers.sum() * fg_fixed_setup
cost_prod_var = (prod_triggers.sum() * fg_batch_size) * fg_var_cost

# FG Value for holding = RM + Var Prod Cost
cost_fg_holding = np.sum(fg_inv * (rm_unit_cost + fg_var_cost) * daily_fg_h_rate)

total_tco = (cost_rm_purchase + cost_rm_ordering + cost_rm_holding + 
             cost_prod_fixed + cost_prod_var + cost_fg_holding)

# --- 4. DASHBOARD DISPLAY ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Service Fill Rate", f"{fill_rate:.1f}%", delta=f"{int(stockout_days)} Stockout Days", delta_color="inverse")
m2.metric("Total System TCO", f"${total_tco:,.0f}")
m3.metric("Production Setup Count", int(prod_triggers.sum()))
m4.metric("Avg FG Capital Tied", f"${(fg_inv.mean() * (rm_unit_cost + fg_var_cost)):,.0f}")

st.subheader("📋 Granular Cost Audit")
breakdown_df = pd.DataFrame({
    "Category": ["Raw Material", "Raw Material", "Raw Material", "Production", "Production", "Finished Goods", "TOTAL"],
    "Component": ["Material Purchase", "Ordering/Fixed PO", "Holding (RM)", "Fixed Setup", "Variable (Volume)", "Holding (FG)", "System TCO"],
    "Value ($)": [cost_rm_purchase, cost_rm_ordering, cost_rm_holding, cost_prod_fixed, cost_prod_var, cost_fg_holding, total_tco]
})
st.table(breakdown_df.style.format({"Value ($)": "{:,.2f}"}))

st.divider()

# --- 5. VISUALIZATIONS ---
st.subheader("📉 The Inventory 'Sawtooth' & Supply Gaps")
viz_df = pd.DataFrame({
    "Day": range(days),
    "RM Inventory": rm_inv,
    "FG Inventory": fg_inv,
    "Stockout Volume": unmet_demand
}).set_index("Day")

st.line_chart(viz_df[["RM Inventory", "FG Inventory"]])
st.area_chart(viz_df["Stockout Volume"], color="#FF4B4B")

st.info(f"**Strategic Insight:** Notice the red peaks. These represent unmet demand. If your Production Lead Time is {prod_lead_time} days, your FG ROP must be high enough to cover demand while the batch is in the oven.")
