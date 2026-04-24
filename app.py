import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(page_title="Supply Chain Performance Auditor", layout="wide")

st.title("📊 Supply Chain Performance Auditor")
st.markdown("---")

# --- 1. SIDEBAR: OPERATIONAL SETTINGS ---
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

# --- 2. ENGINE ---
np.random.seed(42)
daily_demand = np.random.normal(mu_demand, sigma_demand, days).clip(min=0)

fg_inv, rm_inv = np.zeros(days), np.zeros(days)
rm_on_order, fg_in_production = np.zeros(days + rm_lead_time + 1), np.zeros(days + prod_lead_time + 1)
stockout_days = np.zeros(days)

curr_fg, curr_rm = fg_batch_size, rm_order_qty

for t in range(days):
    curr_rm += rm_on_order[t]
    curr_fg += fg_in_production[t]
    
    demand = daily_demand[t]
    if curr_fg >= demand:
        curr_fg -= demand
    else:
        stockout_days[t] = 1
        curr_fg = 0
    
    pipeline_fg = fg_in_production[t+1:].sum()
    if (curr_fg + pipeline_fg) <= fg_trigger_level:
        if curr_rm >= fg_batch_size:
            fg_in_production[t + prod_lead_time] += fg_batch_size
            curr_rm -= fg_batch_size

    pipeline_rm = rm_on_order[t+1:].sum()
    if (curr_rm + pipeline_rm) <= rm_rop:
        rm_on_order[t + rm_lead_time] += rm_order_qty
        
    fg_inv[t], rm_inv[t] = curr_fg, curr_rm

# --- 3. DATA PREPARATION ---
base_chart_data = pd.DataFrame({
    'Day': range(days),
    'RM Inventory': rm_inv,
    'FG Inventory': fg_inv,
    'Daily Demand': daily_demand,
    'Stockout': stockout_days
})

# --- 4. VISUALIZATIONS ---

# Graph A: Demand Curve (Separate)
st.subheader("📈 Daily Demand Curve")
demand_chart = alt.Chart(base_chart_data).mark_area(
    line={'color':'#e45756'},
    color=alt.Gradient(
        gradient='linear',
        stops=[alt.GradientStop(color='white', offset=0),
               alt.GradientStop(color='#e45756', offset=1)],
        x1=1, x2=1, y1=1, y2=0
    ),
    opacity=0.4
).encode(
    x='Day:Q',
    y=alt.Y('Daily Demand:Q', title="Units Demanded")
).properties(height=180)
st.altair_chart(demand_chart, use_container_width=True)

# Graph B: Inventory Movement with Blue Lines & "X" Markers
st.subheader("📦 Inventory Movement & Stockout Alerts")

# Inventory Lines (Blue Tones)
inv_melted = base_chart_data[['Day', 'RM Inventory', 'FG Inventory']].melt('Day', var_name='Type', value_name='Value')
inv_lines = alt.Chart(inv_melted).mark_line().encode(
    x='Day:Q',
    y=alt.Y('Value:Q', title="Inventory Level"),
    color=alt.Color('Type:N', scale=alt.Scale(domain=['RM Inventory', 'FG Inventory'], range=['#1f77b4', '#a6cee3']))
)

# Stockout "X" Markers (Markers sitting at 0)
stockout_pts = base_chart_data[base_chart_data['Stockout'] == 1]
x_markers = alt.Chart(stockout_pts).mark_point(
    shape='cross',
    color='red',
    size=200,
    strokeWidth=3,
    angle=45 # Tilts the cross to make it an 'X'
).encode(
    x='Day:Q',
    y=alt.value(290) # Positions it precisely at the chart baseline
)

st.altair_chart(inv_lines + x_markers, use_container_width=True)

# --- 5. DATA AUDIT TABLES ---
st.divider()
st.subheader("📋 Audit Trail")
col_fg, col_rm = st.columns(2)

with col_fg:
    st.write("**Finished Goods & Service Level**")
    fg_audit = base_chart_data[['Day', 'Daily Demand', 'FG Inventory', 'Stockout']].tail(15)
    st.dataframe(
        fg_audit.style.map(lambda x: 'background-color: #ffcccc' if x == 1 else '', subset=['Stockout']),
        use_container_width=True, hide_index=True
    )

with col_rm:
    st.write("**Raw Material Flows**")
    daily_rm_cons = np.where(pd.Series(np.diff(rm_inv, prepend=curr_rm)) < 0, fg_batch_size, 0)
    rm_audit = pd.DataFrame({'Day': range(days), 'RM Inventory': rm_inv, 'RM Consumption': daily_rm_cons}).tail(15)
    st.dataframe(rm_audit, use_container_width=True, hide_index=True)
