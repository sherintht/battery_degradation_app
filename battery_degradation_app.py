import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Page configuration for a modern look
st.set_page_config(page_title="🔋 Battery Health Simulator", layout="wide")

# --- Attractive Header & Subtitle ---
st.markdown("""
    <div style='text-align:center'>
        <h1 style='color:#60D394; margin-bottom:0'>🔋 Battery Health Simulator</h1>
        <p style='font-size:1.2rem; color:#b8b8b8; margin-top:0'>
            Predict how your habits affect battery health over years. 
            <br>Adjust settings and visualize your battery's future!
        </p>
    </div>
    """, unsafe_allow_html=True)

# --- Sidebar: User Inputs ---
st.sidebar.header("Customize Simulation Parameters")

init_capacity = st.sidebar.number_input("Initial Battery Capacity (mAh)", 500, 10000, 4000, 100)
charge_cycles_per_week = st.sidebar.slider("Charge Cycles per Week", 1, 21, 7)
avg_temp = st.sidebar.slider("Average Operating Temperature (°C)", 10, 60, 25)
charging_habit = st.sidebar.selectbox(
    "Charging Habit", 
    ("Charge to 100% (Full)", "Partial charge (20-80%)", "Fast charging", "Slow charging")
)
depth_of_discharge = st.sidebar.slider("Average Depth of Discharge (%)", 10, 100, 80)
calendar_aging_factor = st.sidebar.slider("Calendar Aging Impact (0=none, 1=high)", 0.0, 1.0, 0.2, 0.05)
years = st.sidebar.slider("Years to Simulate", 1, 10, 5)

# --- Map charging habit to degradation factors ---
habit_factor = {
    "Charge to 100% (Full)": 1.0,
    "Partial charge (20-80%)": 0.6,
    "Fast charging": 1.2,
    "Slow charging": 0.8,
}[charging_habit]

# --- Simulation Function ---
def simulate_battery_soh(
    days,
    charge_cycles_per_week,
    avg_temp,
    habit_factor,
    depth_of_discharge,
    calendar_aging_factor,
    init_capacity
):
    charge_cycles_per_day = charge_cycles_per_week / 7
    SoH = [100.0]  # percent
    times = [0]    # days
    thresholds = {80: None, 60: None}
    for day in range(1, days + 1):
        # Cycle aging: each cycle degrades SoH by a factor
        cycle_deg = (charge_cycles_per_day *
                     0.005 *
                     (depth_of_discharge / 100) *
                     habit_factor)
        # Temperature effect
        temp_factor = np.exp((avg_temp - 25) / 15)
        # Calendar aging
        cal_deg = 0.00005 * calendar_aging_factor
        degrade = (cycle_deg * temp_factor) + cal_deg
        next_soh = SoH[-1] - degrade
        SoH.append(max(next_soh, 0))
        times.append(day)
        for t in thresholds:
            if SoH[-2] >= t > next_soh and thresholds[t] is None:
                thresholds[t] = day / 365  # years
        if next_soh <= 0:
            break
    capacity = [init_capacity * s / 100 for s in SoH]
    return np.array(times), np.array(SoH), capacity, thresholds

# --- Run Simulation ---
days = years * 365
times, SoH, capacities, thresholds = simulate_battery_soh(
    days,
    charge_cycles_per_week,
    avg_temp,
    habit_factor,
    depth_of_discharge,
    calendar_aging_factor,
    init_capacity
)

# --- Dynamic Battery Icon ---
def battery_svg(soh):
    # Color: green >80%, yellow 60-80%, red <60%
    if soh > 80:
        color = "#60D394"
    elif soh > 60:
        color = "#FFA600"
    else:
        color = "#FF4B4B"
    pct = int(soh)
    fill = 1 if pct < 0 else min(1.0, pct / 100)
    svg = f"""
    <svg width="110" height="44">
      <rect x="3" y="8" rx="8" ry="8" width="80" height="28" fill="#232323" stroke="#666" stroke-width="2"/>
      <rect x="7" y="12" rx="5" ry="5" width="{72*fill}" height="20" fill="{color}"/>
      <rect x="85" y="18" width="15" height="8" rx="2" ry="2" fill="#888"/>
      <text x="45" y="30" font-size="16" text-anchor="middle" fill="#eee">{pct}%</text>
    </svg>
    """
    return svg

col1, col2 = st.columns([1, 3])
with col1:
    st.markdown(battery_svg(SoH[-1]), unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; font-size:1.1rem;'>Final SoH</p>", unsafe_allow_html=True)
with col2:
    # --- Interactive Plotly Chart ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times/365, y=SoH, mode='lines+markers', 
        name='State of Health (SoH) %', 
        line=dict(width=3, color="#60D394")
    ))
    fig.add_hline(y=80, line_dash="dash", line_color="orange", annotation_text="80% SoH (Typical EOL)")
    fig.add_hline(y=60, line_dash="dash", line_color="red", annotation_text="60% SoH (Severely Degraded)")
    # Annotate threshold crossings
    for t, val in thresholds.items():
        if val:
            fig.add_vline(x=val, line_dash="dot", line_color="#888",
                annotation_text=f"{t}% @ {val:.1f} yr", annotation_position="top right")
    fig.update_layout(
        xaxis_title="Years",
        yaxis_title="State of Health (%)",
        title="Simulated Battery Degradation Over Time",
        template="plotly_dark",
        height=420,
        margin=dict(l=30, r=20, t=50, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Dynamic Feedback ---
st.markdown("### Result Summary")
if thresholds[80]:
    st.write(f"🔶 Battery drops below **80% SoH** after **{thresholds[80]:.1f} years**.")
else:
    st.write("🟩 Battery stays above **80% SoH** during simulation.")
if thresholds[60]:
    st.write(f"🔴 Battery drops below **60% SoH** after **{thresholds[60]:.1f} years**.")
else:
    st.write("🟨 Battery stays above **60% SoH** during simulation.")
st.write(f"- Final SoH after {years} years: **{SoH[-1]:.2f}%**")
st.write(f"- Final capacity: **{capacities[-1]:.0f} mAh**")

if SoH[-1] < 60:
    st.error("⚠️ Warning: Battery will degrade severely under current conditions!")
elif SoH[-1] < 80:
    st.warning("⚠️ Battery life is moderate. Consider lowering charge cycles, temperature, or depth of discharge.")
else:
    st.success("✅ Your battery health remains high under these conditions.")

# --- Battery Care Tip ---
tips = [
    "💡 Tip: Avoid leaving your battery at 100% for long periods.",
    "💡 Tip: High temperatures speed up battery aging.",
    "💡 Tip: Partial charges are better than full discharges.",
    "💡 Tip: Slow charging can extend battery lifespan.",
    "💡 Tip: Reduce depth of discharge for better longevity."
]
st.info(np.random.choice(tips))

# --- Download CSV ---
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
