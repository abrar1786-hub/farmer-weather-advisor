import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime
 
# ──────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="AgriGuard – Climate Risk Advisor",
    page_icon="🌾",
    layout="centered"
)
 
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&display=swap');
 
html, body, [class*="css"] {
    font-family: 'Sora', sans-serif;
}
 
.risk-card {
    padding: 1.2rem 1.6rem;
    border-radius: 12px;
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 0.8rem;
}
.risk-high   { background: #ffe5e5; color: #c0392b; border-left: 5px solid #c0392b; }
.risk-medium { background: #fff8e1; color: #d68910; border-left: 5px solid #f39c12; }
.risk-safe   { background: #e9fbe9; color: #1e8449; border-left: 5px solid #27ae60; }
.advisory-box {
    background: #f0f4ff;
    border-left: 5px solid #2e86de;
    padding: 1rem 1.4rem;
    border-radius: 10px;
    color: #1a237e;
    font-size: 0.98rem;
}
</style>
""", unsafe_allow_html=True)
 
# ──────────────────────────────────────────────
# API KEY  (put yours in .streamlit/secrets.toml)
# ──────────────────────────────────────────────
try:
    API_KEY = st.secrets["OPENWEATHER_API_KEY"]
except Exception:
    API_KEY = "aafce6cf9cd8393e103087fe9ca4f55a"   # fallback for local dev only
 
# ──────────────────────────────────────────────
# LOAD CROP DATA
# ──────────────────────────────────────────────
@st.cache_data
def load_crop_data():
    with open("crop_data.json") as f:
        return json.load(f)
 
# ──────────────────────────────────────────────
# FETCH & PROCESS WEATHER
# ──────────────────────────────────────────────
def fetch_forecast(city: str) -> pd.DataFrame:
    """
    Hits the OWM 5-day / 3-hour forecast endpoint and
    returns a daily-aggregated DataFrame with columns:
      date, tmax, tmin, humidity, rainfall
    """
    url = (
        f"https://api.openweathermap.org/data/2.5/forecast"
        f"?q={city}&appid={API_KEY}&units=metric"
    )
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        st.error(f"City not found or API error: {resp.json().get('message', 'unknown error')}")
        st.stop()
 
    rows = []
    for item in resp.json()["list"]:
        rows.append({
            "date":     item["dt_txt"].split(" ")[0],
            "tmax":     item["main"]["temp_max"],
            "tmin":     item["main"]["temp_min"],
            "humidity": item["main"]["humidity"],
            "rainfall": item.get("rain", {}).get("3h", 0.0),
        })
 
    df = pd.DataFrame(rows)
    daily = (
        df.groupby("date")
          .agg(tmax=("tmax", "max"),
               tmin=("tmin", "min"),
               humidity=("humidity", "mean"),
               rainfall=("rainfall", "sum"))
          .reset_index()
    )
    # Keep only first 5 calendar days
    daily = daily.head(5).copy()
    daily["tmax"]     = daily["tmax"].round(1)
    daily["tmin"]     = daily["tmin"].round(1)
    daily["humidity"] = daily["humidity"].round(1)
    daily["rainfall"] = daily["rainfall"].round(2)
    return daily
 
# ──────────────────────────────────────────────
# RISK LOGIC  (isolated, no cross-variable leaks)
# ──────────────────────────────────────────────
def heat_risk(tmax: float, crop_tmax: float) -> str:
    if tmax > crop_tmax:
        return "High"
    if tmax >= crop_tmax - 3:
        return "Medium"
    return "Low"
 
def drought_risk(rainfall: float, min_rainfall: float) -> str:
    if rainfall < min_rainfall:
        return "High"
    if rainfall <= min_rainfall + 10:
        return "Medium"
    return "Low"
 
def flood_risk(rainfall: float, max_rainfall: float) -> str:
    if rainfall > max_rainfall:
        return "High"
    if rainfall >= max_rainfall - 10:
        return "Medium"
    return "Low"
 
def pest_risk(humidity: float, crop_humidity: float) -> str:
    if humidity > crop_humidity:
        return "High"
    if humidity >= crop_humidity - 10:
        return "Medium"
    return "Low"
 
def apply_risks(daily: pd.DataFrame, thresholds: dict) -> pd.DataFrame:
    df = daily.copy()
    df["Heat"]    = df.apply(lambda r: heat_risk(r["tmax"],     thresholds["tmax"]),         axis=1)
    df["Drought"] = df.apply(lambda r: drought_risk(r["rainfall"], thresholds["min_rainfall"]), axis=1)
    df["Flood"]   = df.apply(lambda r: flood_risk(r["rainfall"],   thresholds["max_rainfall"]), axis=1)
    df["Pest"]    = df.apply(lambda r: pest_risk(r["humidity"],    thresholds["humidity"]),     axis=1)
    return df
 
# ──────────────────────────────────────────────
# OVERALL RISK  (priority: Heat > Drought > Flood > Pest)
# ──────────────────────────────────────────────
PRIORITY = ["Heat", "Drought", "Flood", "Pest"]
 
def overall_risk(df: pd.DataFrame) -> str:
    for col in PRIORITY:
        if (df[col] == "High").any():
            return col
    return "No major risk"
 
# ──────────────────────────────────────────────
# ADVISORY TEXT
# ──────────────────────────────────────────────
ADVISORY = {
    "Heat":         "🔥 Avoid afternoon field work and increase irrigation frequency.",
    "Drought":      "🌵 Switch to drip irrigation and conserve available water.",
    "Flood":        "🌊 Ensure proper drainage channels are clear and functional.",
    "Pest":         "🐛 Monitor crops closely and apply appropriate pest control.",
    "No major risk": "✅ Conditions look normal. Continue standard farming practices.",
}
 
# ──────────────────────────────────────────────
# COLOUR HELPERS FOR TABLE
# ──────────────────────────────────────────────
RISK_COLORS = {
    "High":   "background-color:#ffe5e5; color:#c0392b; font-weight:600",
    "Medium": "background-color:#fff8e1; color:#d68910; font-weight:600",
    "Low":    "background-color:#e9fbe9; color:#1e8449",
}
 
def style_risk_cell(val):
    return RISK_COLORS.get(val, "")
 
# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────
st.title("🌾 AgriGuard – Climate Risk Advisor")
st.caption("Localized 5-day crop risk prediction powered by OpenWeatherMap")
 
crop_data = load_crop_data()
 
col1, col2 = st.columns([2, 1])
with col1:
    city = st.text_input("📍 Enter City", placeholder="e.g. Chennai, Coimbatore, Delhi")
with col2:
    crop = st.selectbox("🌱 Select Crop", list(crop_data.keys()))
 
run = st.button("🔍 Check Risk", use_container_width=True, type="primary")
 
if run:
    if not city.strip():
        st.warning("Please enter a city name.")
        st.stop()
 
    with st.spinner("Fetching forecast data…"):
        daily     = fetch_forecast(city.strip())
        thresholds = crop_data[crop]
        result    = apply_risks(daily, thresholds)
 
    risk      = overall_risk(result)
    advisory  = ADVISORY[risk]
 
    # ── TABLE ──────────────────────────────────
    st.subheader("📊 5-Day Forecast & Risk Table")
 
    display = result.rename(columns={
        "date": "Date", "tmax": "Tmax (°C)", "tmin": "Tmin (°C)",
        "humidity": "Humidity (%)", "rainfall": "Rainfall (mm)"
    })
 
    styled = (
        display.style
               .applymap(style_risk_cell, subset=["Heat", "Drought", "Flood", "Pest"])
               .format({"Tmax (°C)": "{:.1f}", "Tmin (°C)": "{:.1f}",
                        "Humidity (%)": "{:.1f}", "Rainfall (mm)": "{:.2f}"})
               .set_properties(**{"text-align": "center"})
               .set_table_styles([
                   {"selector": "th", "props": [("text-align", "center"),
                                                ("background", "#f5f5f5"),
                                                ("font-weight", "700")]}
               ])
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)
 
    # ── OVERALL RISK ───────────────────────────
    st.subheader("⚠️ Overall Risk")
 
    if risk == "No major risk":
        css_class = "risk-safe"
        label = "✅ No Major Risk Detected"
    else:
        # Check if any Medium exists across priority columns
        has_medium = any((result[col] == "Medium").any() for col in PRIORITY)
        css_class = "risk-high"
        label = f"🚨 {risk} Risk Detected"
 
    st.markdown(f'<div class="risk-card {css_class}">{label}</div>', unsafe_allow_html=True)
 
    # ── ADVISORY ───────────────────────────────
    st.subheader("🌿 Advisory")
    st.markdown(f'<div class="advisory-box">{advisory}</div>', unsafe_allow_html=True)
 
    # ── CROP THRESHOLDS (collapsible reference) ─
    with st.expander("📋 Crop Thresholds Reference"):
        t = thresholds
        st.markdown(f"""
| Parameter | Threshold |
|---|---|
| Max Temperature | {t['tmax']} °C |
| Min Temperature | {t['tmin']} °C |
| Min Rainfall | {t['min_rainfall']} mm |
| Max Rainfall | {t['max_rainfall']} mm |
| Max Humidity | {t['humidity']} % |
""")
