import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# 1. PAGE SETUP
st.set_page_config(page_title="Supply Chain Auditor Pro", layout="wide")

st.title("🏭 Ultimate Supply Chain Auditor")
st.markdown("---")

# 2. SIDEBAR: PROFESSIONAL PARAMETERS
with st.sidebar:
    st.header("⏱️ Simulation Settings")
    days = st.slider("Timeline (Days)", 100, 730, 365)
    
    st.header("📈 Demand & Risk")
    mu = st.number_input("Average Daily Demand", value=100)
    sigma = st.number_input("Demand Variability", value=25)
    
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

# 3. VECTORIZED ENGINE
np.random.seed(42)
daily_demand = np.random.normal(mu, sigma, days).clip(min=0)

fg_inv, rm_inv = np.zeros(days), np.zeros(days)
rm_on_order = np.zeros(days + rm_lead_time + 1)
fg_in_production = np.zeros(days + prod_lead_time + 1)
prod_triggers, rm_order_triggers = np.zeros(days), np.zeros(days)
unmet_demand, stockout_flag = np.zeros(days), np.zeros(days)

curr_fg, curr_rm = fg_batch_size, rm_order_qty

for t in range(days):
    curr_rm += rm_on_order[t]
    curr_fg += fg_in_production[t]
    
    demand = daily_demand[t]
    if curr_fg >= demand:
        curr_fg -= demand
    else:
        unmet_demand[t] = demand - curr_fg
        stockout_flag[t] = 1 # Flag for the "Wedge"
        curr_fg = 0
    
    pipeline_fg = fg_in_production[t+1:].sum()
    if (curr_fg + pipeline_fg) <= fg_trigger_level:
        if curr_rm >= fg_batch_size:
            fg_in_production[t + prod_lead_time] += fg_batch_size
            curr_rm -= fg_batch_size
            prod_triggers[t] = 1

    pipeline_rm = rm_on_order[t+1:].sum()
    if (curr_rm + pipeline_rm) <= rm_rop:
        rm_on_order[t + rm_lead_time] += rm_order_qty
        rm_order_triggers[t] = 1
        
    fg_inv[t], rm_inv[t] = curr_fg, curr_rm

# 4. METRICS & COSTS
total_demand = np.sum(daily_demand)
fill_rate = ((total_demand - np.sum(unmet_demand)) / total_demand) * 100
daily_rm_h_rate, daily_fg_h_rate = rm_hold_rate / 365, fg_hold_rate / 365

cost_rm_purchase = (rm_order_triggers.sum() * rm_order_qty) * rm_unit_cost
cost_rm_ordering = rm_order_triggers.sum() * rm_order_fixed_cost
cost_rm_holding = np.sum(rm_inv * rm_unit_cost * daily_rm_h_rate)
cost_prod_fixed = prod_triggers.sum() * fg_fixed_setup
cost_prod_var = (prod_triggers.sum() * fg_batch_size) * fg_var_cost
cost_fg_holding = np.sum(fg_inv * (rm_unit_cost + fg_var_cost) * daily_fg_h_rate)
total_tco = cost_rm_purchase + cost_rm_ordering + cost_rm_holding + cost_prod_fixed + cost_prod_var + cost_fg_holding

# 5. UI DASHBOARD
m1, m2, m3, m4 = st.columns(4)
m1.metric("Service Fill Rate", f"{fill_rate:.1f}%")
m2.metric("System TCO", f"${total_tco:,.0f}")
m3.metric("Stockout Days", int(stockout_flag.sum()), delta_color="inverse")
m4.metric("Avg FG Capital", f"${(fg_inv.mean() * (rm_unit_cost + fg_var_cost)):,.0f}")

st.subheader("📋 Granular Cost Audit")
breakdown_df = pd.DataFrame({
    "Component": ["RM Purchase", "RM Ordering", "RM Holding", "Prod Setup", "Prod Variable", "FG Holding"],
    "Value ($)": [cost_rm_purchase, cost_rm_ordering, cost_rm_holding, cost_prod_fixed, cost_prod_var, cost_fg_holding]
})
st.table(breakdown_df.style.format({"Value ($)": "{:,.2f}"}))

# 6. VISUALIZATION WITH "WEDGES"
st.divider()
st.subheader("📈 Inventory Movement & Stockout Wedges")

# Prepare data for Altair
chart_data = pd.DataFrame({
    "Day": range(days),
    "RM Inventory": rm_inv,
    "FG Inventory": fg_inv,
    "Stockout": stockout_flag
}).melt("Day", var_name="Type", value_name="Value")

# Create the Inventory Lines
lines = alt.Chart(chart_data[chart_data['Type'] != 'Stockout']).mark_line().encode(
    x='Day:Q',
    y='Value:Q',
    color=alt.Color('Type:N', scale=alt.Scale(range=['#ffaa00', '#29b5e8']))
)

# Create the "Wedge" Markers (Vertical Rules)
wedges = alt.Chart(pd.DataFrame({"Day": np.where(stockout_flag == 1)[0]})).mark_rule(
    color='red', strokeWidth=2, strokeDash=[4,4]
).encode(x='Day:Q')

# Combine charts
st.altair_chart(lines + wedges, use_container_width=True)

st.info("💡 **Auditor Insight:** The red vertical dashed lines (wedges) mark the exact days demand was missed. This allows you to trace if a stockout was caused by a late Raw Material arrival or a slow Production Lead Time.")
