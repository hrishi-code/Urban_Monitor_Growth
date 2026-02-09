import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import plotly.graph_objects as go
import time

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Urban Growth Monitor",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for that "High-Tech" Dark Look
st.markdown("""
<style>
    .stApp {background-color: #0e1117;}
    div.stButton > button {
        background-color: #00d26a; color: white; border-radius: 8px; 
        font-weight: bold; width: 100%; height: 50px;
    }
    div.stButton > button:hover {background-color: #00b359;}
    .metric-card {background-color: #1f2937; padding: 15px; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SIDEBAR CONTROL PANEL
# ==========================================
with st.sidebar:
    st.title("🏙️ Urban Monitor")
    st.markdown("---")
    
    # Inputs
    city = st.selectbox("Select Target City", ["Pune", "Mumbai", "Delhi", "Bangalore"])
    year_range = st.slider("Analysis Period", 2017, 2023, (2018, 2023))
    
    st.markdown("### ⚙️ Filters")
    show_poi = st.checkbox("Correlate with POI Data", value=True)
    show_anomalies = st.checkbox("Highlight Lockdown Dips", value=True)
    
    st.markdown("---")
    # The Big Button
    predict_btn = st.button("🚀 Analyze & Predict")
    
    # Status Indicator
    api_status = st.empty()

# ==========================================
# 3. HELPER: FETCH DATA FROM BACKEND
# ==========================================
def fetch_live_data(city_name):
    """
    Tries to get real data from Member 2's API.
    If API is down, returns Fake Demo Data.
    """
    api_url = f"http://127.0.0.1:8000/get-data?city={city_name}"
    
    try:
        response = requests.get(api_url, timeout=3) # 3 sec timeout
        if response.status_code == 200:
            return response.json(), True # Success
    except:
        pass
    
    # FALLBACK DEMO DATA (If Backend is off)
    return {
        "city": city_name,
        "avg_radiance": 45.2 if city_name == "Pune" else 62.1,
        "growth_rate": 2.4,
        "status": "High Growth 🟢",
        "confidence": "87.5%",
        "source": "Demo Mode (Backend Offline)"
    }, False

# ==========================================
# 4. MAIN DASHBOARD LAYOUT
# ==========================================
st.markdown(f"## 🛰️ Economic Growth Analysis: **{city}**")

# Logic: Only show results if button clicked OR if we already have a state
if predict_btn:
    
    with st.spinner(f"🛰️ Contacting Satellite Server & Running XGBoost for {city}..."):
        time.sleep(1) # Fake loading for effect
        data, is_live = fetch_live_data(city)
    
    # Show Connection Status in Sidebar
    if is_live:
        api_status.success("🟢 Backend Connected")
    else:
        api_status.warning("⚠️ Backend Offline (Showing Demo)")

    # --- ROW 1: KEY METRICS ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Avg Night Light", f"{data['avg_radiance']} nW", "VIIRS DNB")
    col2.metric("Growth Rate", f"{data['growth_rate']}%", "MoM")
    col3.metric("AI Status", data['status'])
    col4.metric("Model Confidence", data['confidence'], "GaussianNB")

    st.markdown("---")

    # --- ROW 2: MAP & CHARTS ---
    left_col, right_col = st.columns((2, 1))

    with left_col:
        st.subheader("📍 Growth Hotspots")
        
        # MAP LOGIC
        # We generate a few random points around the city center to simulate 'zones'
        lat_centers = {"Pune": 18.52, "Mumbai": 19.07, "Delhi": 28.70, "Bangalore": 12.97}
        lon_centers = {"Pune": 73.85, "Mumbai": 72.87, "Delhi": 77.10, "Bangalore": 77.59}
        
        base_lat = lat_centers[city]
        base_lon = lon_centers[city]
        
        # Generate 50 fake "sub-districts"
        map_data = pd.DataFrame({
            'lat': np.random.normal(base_lat, 0.05, 50),
            'lon': np.random.normal(base_lon, 0.05, 50),
            'intensity': np.random.randint(10, 100, 50)
        })
        
        fig_map = px.density_mapbox(
            map_data, lat='lat', lon='lon', z='intensity', radius=20,
            center=dict(lat=base_lat, lon=base_lon), zoom=10,
            mapbox_style="carto-darkmatter",
            title="Night Light Intensity Clusters"
        )
        st.plotly_chart(fig_map, use_container_width=True)

    with right_col:
        st.subheader("📈 Trend & Forecast")
        
        # 1. Historical Trend (Line Chart)
        dates = pd.date_range(start='2022-01-01', periods=12, freq='M')
        # Create a trend that matches the "Growth Rate"
        trend_values = np.linspace(40, data['avg_radiance'], 12) + np.random.normal(0, 2, 12)
        
        fig_line = px.line(x=dates, y=trend_values, labels={'x': 'Date', 'y': 'Radiance'})
        fig_line.update_layout(template="plotly_dark", title="Last 12 Months", height=250)
        st.plotly_chart(fig_line, use_container_width=True)
        
        # 2. Prediction (Bar Chart)
        st.subheader("🔮 Next Month Prediction")
        next_val = data['avg_radiance'] * (1 + (data['growth_rate']/100))
        
        fig_bar = go.Figure(go.Indicator(
            mode = "number+delta",
            value = next_val,
            delta = {'position': "top", 'reference': data['avg_radiance']},
            title = {"text": "Predicted Radiance"},
            domain = {'x': [0, 1], 'y': [0, 1]}
        ))
        fig_bar.update_layout(template="plotly_dark", height=200)
        st.plotly_chart(fig_bar, use_container_width=True)

else:
    # Initial State (Before clicking button)
    st.info("👈 Select a city and click 'Analyze & Predict' to start the Satellite Pipeline.")
    
    # Cool background image
    st.image("https://upload.wikimedia.org/wikipedia/commons/e/e4/India_at_night.jpg", 
             caption="VIIRS Nighttime Lights of India", use_column_width=True)