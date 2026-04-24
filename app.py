import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# 1. PAGE SETUP
st.set_page_config(page_title="Supply Chain Performance Auditor", layout="wide")

st.title("📊 Supply Chain Performance Auditor")
st.markdown("---")

# --- 2. SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("🔄 Scenario Control")
    # Button to refresh demand data
    if st.button("Generate New Demand Scenario"):
        if 'demand_seed' not in st.session_state:
            st.session_state.demand_seed = 0
        st.session_state.demand_seed += 1
    
    st.header("⏱️ Simulation Settings")
    days = st.slider("Time Horizon (Days)", 100, 730, 365)
    
    st.header("📈 Demand & Risk")
    mu_demand = st.number_input("Average Daily Demand", value=100)
    sigma_demand = st.number_input("Demand Variability (Std Dev)", value=25)
    
    st.header("🏗️ Raw Material (RM) Policy")
    rm_order_qty = st.number_input("RM Order Quantity (Q)", value=5000)
    rm_rop = st.number_input("RM Reorder Point (ROP)", value=2500)
    rm_lead_time = st.slider("RM Lead Time (Days)", 1, 14, 5)
    rm_unit_cost = st.number_input("RM Unit Cost ($)", value=25.0)
    rm_order_fixed_cost = st.number_input("Fixed Cost per RM Order ($)", value=300.0)
    rm_hold_rate = st.slider("RM Annual Holding Rate (%)", 5, 50, 15) / 100
    
    st.header("📦 Production (FG) Policy")
    fg_batch_size = st.number_input("Production Batch Size", value=1500)
    fg_trigger_level = st.number_input("Production Trigger (FG ROP)", value=800)
    prod_lead_time = st.slider("Production Lead Time (Days)", 1, 14, 3)
    fg_fixed_setup = st.number_input("Setup Cost per Batch ($)", value=2000.0)
    fg_var_cost = st.number_input("Variable Prod Cost/Unit ($)", value=15.0)
    fg_hold_rate = st.slider("FG Annual Holding Rate (%)", 5, 50, 25) / 100

# --- 3. DEMAND GENERATION (LOCKED VIA SESSION STATE) ---
if 'demand_seed' not in st.session_state:
    st.session_state.demand_seed = 42

np.random.seed(st.session_state.demand_seed)
daily_demand = np.random.normal(mu_demand, sigma_demand, days).clip(min=0)

# --- 4. THE SIMULATION ENGINE ---
fg_inv, rm_inv = np.zeros(days), np.zeros(days)
rm_on_order = np.zeros(days + rm_lead_time + 1)
fg_in_production = np.zeros(days + prod_lead_time + 1)
prod_triggers, rm_order_triggers = np.zeros(days), np.zeros(days)
unmet_demand, stockout_flag = np.zeros(days), np.zeros(days)

# CORRECTED LOGIC: Opening balance covers Lead Time + a small buffer 
# (Total demand during Lead Time) * 1.5 usually provides a realistic start
curr_fg = (mu_demand * prod_lead_time) * 1.5 
curr_rm = rm_order_qty

for t in range(days):
    curr_rm += rm_on_order[t]
    curr_fg += fg_in_production[t]
    
    demand = daily_demand[t]
    if curr_fg < demand:
        unmet_demand[t] = demand - curr_fg
        stockout_flag[t] = 1
        curr_fg = 0
    else:
        curr_fg -= demand
    
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

# --- 5. KPIs & COSTS ---
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

# --- 6. UI DASHBOARD ---
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Service Fill Rate", f"{fill_rate:.1f}%")
k2.metric("Stockout Days", int(stockout_flag.sum()), delta_color="inverse")
k3.metric("System TCO", f"${total_tco:,.0f}")
k4.metric("Avg FG Inventory", f"{fg_inv.mean():,.0f}")
k5.metric("Avg RM Inventory", f"{rm_inv.mean():,.0f}")

st.divider()

# --- 7. COST TABLE ---
st.subheader("📝 Granular Cost Breakup")
breakdown_df = pd.DataFrame([
    {"Component": "RM Purchase", "Value ($)": cost_rm_purchase},
    {"Component": "RM Ordering", "Value ($)": cost_rm_ordering},
    {"Component": "RM Holding", "Value ($)": cost_rm_holding},
    {"Component": "Prod Setup", "Value ($)": cost_prod_fixed},
    {"Component": "Prod Variable", "Value ($)": cost_prod_var},
    {"Component": "FG Holding", "Value ($)": cost_fg_holding},
    {"Component": "TOTAL SYSTEM COST", "Value ($)": total_tco}
])

st.table(breakdown_df.style.format({"Value ($)": "{:,.2f}"}).map(
    lambda x: 'font-weight: bold; background-color: #333333' if x == "TOTAL SYSTEM COST" else '', 
    subset=['Component']
))

st.divider()

# --- 8. VISUALS ---
st.subheader("📈 Daily Demand Curve")
demand_df = pd.DataFrame({'Day': range(days), 'Demand': daily_demand})
st.altair_chart(alt.Chart(demand_df).mark_area(line={'color':'#e45756'}, opacity=0.3, color='#e45756').encode(
    x='Day:Q', y='Demand:Q'
).properties(height=150), use_container_width=True)

st.subheader("📦 Inventory Movement & Stockout Alerts")
inv_df = pd.DataFrame({'Day': range(days), 'RM Inventory': rm_inv, 'FG Inventory': fg_inv, 'Stockout': stockout_flag})
inv_melted = inv_df[['Day', 'RM Inventory', 'FG Inventory']].melt('Day', var_name='Type', value_name='Value')

lines = alt.Chart(inv_melted).mark_line().encode(
    x='Day:Q', y='Value:Q',
    color=alt.Color('Type:N', scale=alt.Scale(domain=['RM Inventory', 'FG Inventory'], range=['#1f77b4', '#a6cee3']))
)

# Stockout "X" Markers
x_marks = alt.Chart(inv_df[inv_df['Stockout'] == 1]).mark_point(
    shape='cross', color='red', size=200, strokeWidth=3, angle=45
).encode(x='Day:Q', y=alt.value(290))

st.altair_chart(lines + x_marks, use_container_width=True)

st.subheader("📋 Audit Trail (Last 15 Days)")
audit_df = pd.DataFrame({
    'Day': range(days), 'Demand': daily_demand, 'FG Inv': fg_inv, 'RM Inv': rm_inv, 'Stockout': stockout_flag
}).tail(15)
st.dataframe(
    audit_df.style.map(lambda x: 'background-color: #442222' if x == 1 else '', subset=['Stockout']),
    use_container_width=True, hide_index=True
)
