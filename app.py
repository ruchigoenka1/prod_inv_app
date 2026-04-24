import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="Supply Chain Performance Auditor", layout="wide")

st.title("📊 Supply Chain Performance Auditor")
st.markdown("---")

# 1. SIDEBAR: SIMULATION & OPERATIONAL SETTINGS
# --- Features: Demand Variability, Production Time, Stockout Logic ---
with st.sidebar:
    st.header("⏱️ Simulation Settings")
    days = st.slider("Time Horizon (Days)", 100, 730, 365)
    
    st.header("📈 Demand Profile")
    mu_demand = st.number_input("Average Daily Demand", value=100)
    sigma_demand = st.number_input("Demand Variability (Std Dev)", value=25)
    
    st.header("🏗️ Raw Material (RM) Policy")
    rm_order_qty = st.number_input("RM Order Quantity (Q)", value=5000)
    rm_rop = st.number_input("RM Reorder Point (ROP)", value=2500)
    rm_lead_time = st.slider("RM Lead Time (Days)", 1, 14, 5)
    
    st.header("📦 Production (FG) Policy")
    fg_batch_size = st.number_input("Production Batch Size", value=1500)
    fg_trigger_level = st.number_input("FG Reorder Point (ROP)", value=800)
    prod_lead_time = st.slider("Production Lead Time (Days)", 1, 14, 3)

# 2. VECTORIZED SIMULATION ENGINE (Integrated with Lead Times and ROP)
np.random.seed(42)
daily_demand = np.random.normal(mu_demand, sigma_demand, days).clip(min=0)

# Arrays for state tracking
fg_inv, rm_inv = np.zeros(days), np.zeros(days)
rm_on_order, fg_in_production = np.zeros(days + rm_lead_time + 1), np.zeros(days + prod_lead_time + 1)
stockout_days = np.zeros(days)

curr_fg, curr_rm = fg_batch_size, rm_order_qty

for t in range(days):
    curr_rm += rm_on_order[t]
    curr_fg += fg_in_production[t]
    
    # Daily Demand Consumption & Stockout Check
    demand = daily_demand[t]
    if curr_fg >= demand:
        curr_fg -= demand
    else:
        # Stockout occurs
        stockout_days[t] = 1
        curr_fg = 0
    
    # Production Trigger (FG ROP)
    pipeline_fg = fg_in_production[t+1:].sum()
    if (curr_fg + pipeline_fg) <= fg_trigger_level:
        if curr_rm >= fg_batch_size:
            fg_in_production[t + prod_lead_time] += fg_batch_size
            curr_rm -= fg_batch_size

    # Raw Material Reorder Trigger (RM ROP)
    pipeline_rm = rm_on_order[t+1:].sum()
    if (curr_rm + pipeline_rm) <= rm_rop:
        rm_on_order[t + rm_lead_time] += rm_order_qty
        
    fg_inv[t], rm_inv[t] = curr_fg, curr_rm

# 3. METRICS & OPERATIONAL AUDIT
total_stockout_days = int(stockout_days.sum())
fill_rate = ((np.sum(daily_demand) - np.sum(np.where(stockout_days==1, daily_demand, 0))) / np.sum(daily_demand)) * 100

c1, c2, c3 = st.columns(3)
c1.metric("Service Fill Rate", f"{fill_rate:.1f}%")
c2.metric("Total Stockout Days", total_stockout_days)
c3.metric("Avg FG Inventory", f"{fg_inv.mean():,.0f}")

st.divider()

# 4. ENHANCED VISUALIZATION: INVENTORY MOVEMENTS & STOCKOUT WEDGES
st.subheader("Inventory Movement & Stockout Wedges")

# Multi-layered chart with Demand, Inventories, and markers
base_chart_data = pd.DataFrame({
    'Day': range(days),
    'RM Inventory': rm_inv,
    'FG Inventory': fg_inv,
    'Daily Demand': daily_demand,
    'Stockout': stockout_days
}).set_index('Day')

# Continuous Inventory Lines
lines_chart = alt.Chart(base_chart_data.reset_index().melt('Day', var_name='Type', value_name='Value')).mark_line().encode(
    x='Day:Q',
    y='Value:Q',
    color=alt.Color('Type:N', scale=alt.Scale(range=['#4c78a8', '#f58518', '#e45756'])) # Custom colors
)

# Demand Graph as an area chart in the background
demand_area = alt.Chart(base_chart_data.reset_index()).mark_area(opacity=0.3, color='#e45756').encode(
    x='Day:Q',
    y='Daily Demand:Q'
)

# Stockout "Wedge" Markers (Discrete Mark Rules)
wedge_markers = alt.Chart(base_chart_data[base_chart_data['Stockout'] == 1].reset_index()).mark_rule(color='red', strokeWidth=2).encode(
    x='Day:Q',
    y=alt.Y('FG Inventory:Q', scale=alt.Scale(domain=[0, 100])), # Placed at the very bottom
    y2=alt.value(0) # Extends to zero
)

# Combined Chart (layered)
layered_chart = alt.layer(demand_area, lines_chart, wedge_markers).resolve_scale(y='independent')
st.altair_chart(layered_chart, use_container_width=True)

st.divider()

# 5. GRANULAR DATA AUDIT TABLES
st.subheader("📋 Granular Operational Data (Audit Trail)")
col_fg, col_rm = st.columns(2)

with col_fg:
    st.write("**Finished Goods Inventory & Service Level**")
    fg_audit_df = base_chart_data[['Daily Demand', 'FG Inventory', 'Stockout']].tail(20)
    st.dataframe(fg_audit_df.style.applymap(lambda x: 'background-color: lightcoral' if x == 1 else '', subset=['Stockout']), use_container_width=True)

with col_rm:
    st.write("**Raw Material Availability & Consumption**")
    # Simulate a daily consumption for table view
    daily_rm_cons = np.where(pd.Series(np.diff(rm_inv, prepend=curr_rm)) < 0, fg_batch_size, 0)
    rm_audit_df = pd.DataFrame({'RM Inventory': rm_inv, 'RM Consumption': daily_rm_cons}, index=base_chart_data.index).tail(20)
    st.dataframe(rm_audit_df, use_container_width=True)

st.info("💡 **Auditor Insight:** The red vertical rules (wedges) appear only on days where stockout is 1. Notice how Stockout 1 corresponds to where the FG line hits the baseline. If these red wedges appear despite having high RM inventory, the root cause is a production line constraint, not material availability.")
