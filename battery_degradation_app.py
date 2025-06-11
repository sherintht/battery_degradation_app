import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(page_title="Battery Health & Degradation Estimator", layout="centered")

st.title("🔋 Battery Health & Degradation Estimator (Simulated Data)")

st.markdown("""
This interactive app estimates battery **State of Health (SoH)** over time based on your habits and environment.
""")

# Sidebar for parameter input
st.sidebar.header("Customize Simulation Parameters")

# User Inputs
init_capacity = st.sidebar.number_input("Initial Battery Capacity (mAh)", min_value=500, max_value=10000, value=4000, step=100)
charge_cycles_per_week = st.sidebar.slider("Charge Cycles per Week", min_value=1, max_value=21, value=7)
avg_temp = st.sidebar.slider("Average Operating Temperature (°C)", min_value=10, max_value=60, value=25)
charging_habit = st.sidebar.selectbox(
    "Charging Habit", 
    ("Charge to 100% (Full)", "Partial charge (20-80%)", "Fast charging", "Slow charging")
)
depth_of_discharge = st.sidebar.slider("Average Depth of Discharge (%)", min_value=10, max_value=100, value=80)
calendar_aging_factor = st.sidebar.slider("Calendar Aging Impact (0=none, 1=high)", min_value=0.0, max_value=1.0, value=0.2, step=0.05)

# Simulation Duration
years = st.sidebar.slider("Years to Simulate", 1, 10, 3)
days = years * 365

# Map charging habit to degradation factors
habit_factor = {
    "Charge to 100% (Full)": 1.0,
    "Partial charge (20-80%)": 0.6,
    "Fast charging": 1.2,
    "Slow charging": 0.8,
}[charging_habit]

# Basic simulation model (simplified, for demonstration)
def simulate_battery_soh(
    days,
    charge_cycles_per_week,
    avg_temp,
    habit_factor,
    depth_of_discharge,
    calendar_aging_factor,
    init_capacity
):
    # Daily calculations
    charge_cycles_per_day = charge_cycles_per_week / 7
    SoH = [100.0]  # percent
    times = [0]    # days
    thresholds = {80: None, 60: None}
    for day in range(1, days + 1):
        # Cycle aging: Assume each cycle degrades SoH by a factor, affected by depth of discharge and habit
        cycle_deg = (charge_cycles_per_day *
                     0.005 *  # base rate per cycle
                     (depth_of_discharge / 100) *
                     habit_factor)
        # Temperature accelerates degradation (Arrhenius-like)
        temp_factor = np.exp((avg_temp - 25) / 15)  # more aggressive above 25°C
        
        # Calendar aging (time-based, independent of cycles)
        cal_deg = 0.00005 * calendar_aging_factor

        # Total degradation per day
        degrade = (cycle_deg * temp_factor) + cal_deg
        next_soh = SoH[-1] - degrade
        SoH.append(max(next_soh, 0))
        times.append(day)

        # Record when SoH crosses below thresholds
        for t in thresholds:
            if SoH[-2] >= t > next_soh and thresholds[t] is None:
                thresholds[t] = day / 365  # years
        if next_soh <= 0:
            break
    # Calculate remaining capacity over time
    capacity = [init_capacity * s / 100 for s in SoH]
    return np.array(times), np.array(SoH), capacity, thresholds

times, SoH, capacities, thresholds = simulate_battery_soh(
    days,
    charge_cycles_per_week,
    avg_temp,
    habit_factor,
    depth_of_discharge,
    calendar_aging_factor,
    init_capacity
)

# Visualization
fig, ax = plt.subplots()
ax.plot(times / 365, SoH, label="State of Health (SoH) %")
ax.axhline(80, color='orange', linestyle='--', label='80% SoH (Typical EOL)')
ax.axhline(60, color='red', linestyle='--', label='60% SoH (Severely Degraded)')
ax.set_xlabel("Time (Years)")
ax.set_ylabel("State of Health (%)")
ax.set_title("Simulated Battery Degradation Over Time")
ax.set_ylim(0, 105)
ax.legend()

# Highlight threshold crossings
for t, val in thresholds.items():
    if val:
        ax.axvline(val, linestyle=":", color="gray")
        ax.annotate(f"{t}% @ {val:.1f} yr", (val, t), textcoords="offset points", xytext=(10,10), ha='left')

st.pyplot(fig)

# Summary
st.markdown("### Result Summary")
st.write(f"**Initial Capacity:** {init_capacity} mAh")
if thresholds[80]:
    st.write(f"- Battery drops below **80% SoH** after **{thresholds[80]:.1f} years**.")
else:
    st.write("- Battery stays above 80% SoH during simulation.")
if thresholds[60]:
    st.write(f"- Battery drops below **60% SoH** after **{thresholds[60]:.1f} years**.")
else:
    st.write("- Battery stays above 60% SoH during simulation.")

st.write(f"- Final SoH after {years} years: **{SoH[-1]:.2f}%**")
st.write(f"- Final capacity: **{capacities[-1]:.0f} mAh**")

# Allow download as CSV
csv_data = pd.DataFrame({
    "Day": times,
    "Year": times/365,
    "SoH (%)": SoH,
    "Capacity (mAh)": capacities
})
csv_bytes = csv_data.to_csv(index=False).encode()
st.download_button(
    label="📥 Download Simulation Data (CSV)",
    data=csv_bytes,
    file_name="battery_simulation_results.csv",
    mime="text/csv"
)

st.info("Adjust parameters in the sidebar to see real-time updates in battery health simulation.")
