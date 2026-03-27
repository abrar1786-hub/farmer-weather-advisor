import streamlit as st
import requests
import pandas as pd
import json
import plotly.graph_objects as go
from datetime import datetime

# ──────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="AgriGuard – Climate Risk Advisor",
    page_icon="🌾",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.hero-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.4rem;
    color: #1a3a1a;
    letter-spacing: -0.5px;
    margin-bottom: 0;
    line-height: 1.15;
}
.hero-sub { font-size: 0.92rem; color: #6b7c6b; margin-top: 3px; font-weight: 300; }

.metric-row { display: flex; gap: 10px; margin: 16px 0; flex-wrap: wrap; }
.metric-tile {
    flex: 1; min-width: 100px;
    background: #f4f9f4;
    border: 1px solid #d4e8d4;
    border-radius: 12px;
    padding: 12px 14px;
    text-align: center;
}
.metric-tile .val { font-size: 1.35rem; font-weight: 600; color: #1a3a1a; }
.metric-tile .lbl { font-size: 0.72rem; color: #6b7c6b; text-transform: uppercase; letter-spacing: 0.5px; }

.badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
.badge-High   { background:#ffe0e0; color:#b71c1c; }
.badge-Medium { background:#fff8e1; color:#e65100; }
.badge-Low    { background:#e8f5e9; color:#1b5e20; }

.risk-card {
    border-radius: 14px; padding: 18px 24px; margin: 12px 0;
    font-size: 1.1rem; font-weight: 600;
    display: flex; align-items: center; gap: 10px;
}
.risk-danger { background:#fdecea; border:1.5px solid #f44336; color:#b71c1c; }
.risk-warn   { background:#fff8e1; border:1.5px solid #ffc107; color:#e65100; }
.risk-safe   { background:#e8f5e9; border:1.5px solid #4caf50; color:#1b5e20; }

.advisory {
    background: linear-gradient(135deg, #f0faf0, #e8f5e9);
    border-left: 5px solid #388e3c;
    border-radius: 10px;
    padding: 14px 18px;
    color: #1b5e20;
    font-size: 0.93rem;
    line-height: 1.65;
}

.section-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.2rem;
    color: #1a3a1a;
    border-bottom: 2px solid #c8e6c9;
    padding-bottom: 5px;
    margin: 24px 0 12px 0;
}

.thresh-table { width:100%; border-collapse:collapse; font-size:0.86rem; }
.thresh-table th { background:#e8f5e9; color:#2e7d32; padding:8px 12px; text-align:left; font-weight:600; }
.thresh-table td { padding:7px 12px; border-bottom:1px solid #f0f0f0; color:#333; }
.thresh-table tr:last-child td { border-bottom:none; }

/* forecast table */
.forecast-table { width:100%; border-collapse:collapse; font-size:0.85rem; }
.forecast-table th {
    background:#2e7d32; color:#fff;
    padding:9px 11px; text-align:center; font-weight:600;
}
.forecast-table td { padding:8px 10px; border-bottom:1px solid #eef4ee; text-align:center; }
.forecast-table tr:nth-child(even) td { background:#f7fbf7; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# API KEY
# ──────────────────────────────────────────────
try:
    API_KEY = st.secrets["OPENWEATHER_API_KEY"]
except Exception:
    API_KEY = "aafce6cf9cd8393e103087fe9ca4f55a"

# ──────────────────────────────────────────────
# LOAD CROP DATA
# ──────────────────────────────────────────────
@st.cache_data
def load_crop_data():
    with open("crop_data.json") as f:
        return json.load(f)

# ──────────────────────────────────────────────
# FETCH WEATHER
# ──────────────────────────────────────────────
def fetch_forecast(city: str) -> pd.DataFrame:
    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        f"?q={city}&appid={API_KEY}&units=metric"
    )
    try:
        resp = requests.get(url, timeout=12)
    except requests.exceptions.ConnectionError:
        st.error("❌ Network error. Please check your connection.")
        st.stop()
    except requests.exceptions.Timeout:
        st.error("❌ Request timed out. Try again.")
        st.stop()

    if resp.status_code == 401:
        st.error("❌ Invalid API key.")
        st.stop()
    if resp.status_code == 404:
        st.error(f"❌ City **'{city}'** not found. Try a different spelling.")
        st.stop()
    if resp.status_code != 200:
        st.error(f"❌ API error {resp.status_code}: {resp.json().get('message', 'unknown')}")
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

    df    = pd.DataFrame(rows)
    daily = (
        df.groupby("date")
          .agg(tmax=("tmax", "max"),
               tmin=("tmin", "min"),
               humidity=("humidity", "mean"),
               rainfall=("rainfall", "sum"))
          .reset_index()
    )
    daily["tmax"]     = daily["tmax"].round(1)
    daily["tmin"]     = daily["tmin"].round(1)
    daily["humidity"] = daily["humidity"].round(1)
    daily["rainfall"] = daily["rainfall"].round(2)
    return daily.head(5).copy()

# ──────────────────────────────────────────────
# RISK FUNCTIONS  — strictly isolated
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
    # Zero rainfall can never be a flood risk
    if rainfall == 0.0:
        return "Low"
    if rainfall > max_rainfall:
        return "High"
    if rainfall >= max_rainfall - 10:
        return "Medium"
    return "Low"


def pest_risk(humidity: float, tmin: float, crop_humidity: float) -> str:
    # Pest activity negligible in cold weather (tmin < 10°C)
    if tmin < 10.0:
        return "Low"
    if humidity > crop_humidity:
        return "High"
    if humidity >= crop_humidity - 10:
        return "Medium"
    return "Low"


def apply_risks(daily: pd.DataFrame, thresholds: dict) -> pd.DataFrame:
    df = daily.copy()
    df["Heat"]    = df.apply(lambda r: heat_risk(r["tmax"], thresholds["tmax"]), axis=1)
    df["Drought"] = df.apply(lambda r: drought_risk(r["rainfall"], thresholds["min_rainfall"]), axis=1)
    df["Flood"]   = df.apply(lambda r: flood_risk(r["rainfall"], thresholds["max_rainfall"]), axis=1)
    df["Pest"]    = df.apply(lambda r: pest_risk(r["humidity"], r["tmin"], thresholds["humidity"]), axis=1)
    return df

# ──────────────────────────────────────────────
# OVERALL RISK  (Heat > Drought > Flood > Pest)
# ──────────────────────────────────────────────
PRIORITY = ["Heat", "Drought", "Flood", "Pest"]

def overall_risk(df: pd.DataFrame):
    for col in PRIORITY:
        if (df[col] == "High").any():
            return col, "High"
    for col in PRIORITY:
        if (df[col] == "Medium").any():
            return col, "Medium"
    return "No major risk", "None"

# ──────────────────────────────────────────────
# ADVISORY TEXT
# ──────────────────────────────────────────────
ADVISORY = {
    "Heat": (
        "🔥 <b>Heat Advisory:</b> Temperatures are exceeding safe limits for your crop. "
        "Avoid fieldwork between 11 AM–3 PM. Increase irrigation frequency and consider "
        "shade netting for vulnerable seedlings."
    ),
    "Drought": (
        "🌵 <b>Drought Advisory:</b> Rainfall is below the minimum required for healthy growth. "
        "Switch to drip or sprinkler irrigation immediately. Mulch the soil to retain moisture "
        "and avoid unnecessary tillage that increases evaporation."
    ),
    "Flood": (
        "🌊 <b>Flood Advisory:</b> Excessive rainfall is expected. Ensure drainage channels are "
        "clear and functional. Consider raised-bed cultivation and avoid applying fertilizers "
        "before heavy rain to prevent runoff."
    ),
    "Pest": (
        "🐛 <b>Pest Advisory:</b> High humidity is creating favorable conditions for pests and "
        "fungal disease. Scout fields every 2 days, apply appropriate fungicides/pesticides "
        "as a preventive measure, and improve air circulation if possible."
    ),
    "No major risk": (
        "✅ <b>Conditions look normal</b> for your selected crop. Continue standard farming "
        "practices. Monitor forecasts daily and stay prepared for sudden weather changes."
    ),
}

# ──────────────────────────────────────────────
# CHARTS
# ──────────────────────────────────────────────
def temp_chart(df: pd.DataFrame, crop_tmax: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["tmax"], mode="lines+markers",
        name="Tmax (°C)", line=dict(color="#e53935", width=2.5), marker=dict(size=7)
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["tmin"], mode="lines+markers",
        name="Tmin (°C)", line=dict(color="#1e88e5", width=2.5), marker=dict(size=7),
        fill="tonexty", fillcolor="rgba(144,202,249,0.15)"
    ))
    # Crop threshold line
    fig.add_hline(
        y=crop_tmax, line_dash="dot", line_color="#ff7043",
        annotation_text=f"Crop max {crop_tmax}°C",
        annotation_position="top left"
    )
    fig.update_layout(
        title="Temperature Forecast vs Crop Threshold",
        xaxis_title="Date", yaxis_title="°C",
        height=300, margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", y=-0.3),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", size=12),
        xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#f0f0f0"),
    )
    return fig


def rain_chart(df: pd.DataFrame, min_rain: float, max_rain: float) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=df["date"], y=df["rainfall"],
        marker_color="#43a047", marker_line_color="#2e7d32", marker_line_width=1.2,
        name="Rainfall (mm)"
    ))
    fig.add_hline(y=min_rain, line_dash="dot", line_color="#f57f17",
                  annotation_text=f"Min {min_rain}mm", annotation_position="top left")
    fig.add_hline(y=max_rain, line_dash="dot", line_color="#c62828",
                  annotation_text=f"Max {max_rain}mm", annotation_position="top left")
    fig.update_layout(
        title="Daily Rainfall vs Crop Thresholds",
        xaxis_title="Date", yaxis_title="mm",
        height=280, margin=dict(l=0, r=0, t=40, b=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", size=12),
        xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#f0f0f0"),
    )
    return fig


def risk_heatmap(result: pd.DataFrame) -> go.Figure:
    risk_map = {"Low": 0, "Medium": 1, "High": 2}
    risk_cols = ["Heat", "Drought", "Flood", "Pest"]
    z    = [[risk_map[result[col].iloc[i]] for col in risk_cols] for i in range(len(result))]
    text = [[result[col].iloc[i]           for col in risk_cols] for i in range(len(result))]

    fig = go.Figure(go.Heatmap(
        z=z, x=risk_cols, y=result["date"].tolist(),
        text=text, texttemplate="%{text}",
        colorscale=[[0, "#e8f5e9"], [0.5, "#fff8e1"], [1, "#fdecea"]],
        showscale=False, xgap=4, ygap=4,
    ))
    fig.update_layout(
        title="Risk Heatmap (5 Days × 4 Types)",
        height=260, margin=dict(l=0, r=0, t=40, b=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", size=12),
        yaxis=dict(autorange="reversed"),
    )
    return fig

# ──────────────────────────────────────────────
# BADGE HTML HELPER
# ──────────────────────────────────────────────
def badge(val: str) -> str:
    return f'<span class="badge badge-{val}">{val}</span>'

# ──────────────────────────────────────────────
# ─── UI ───────────────────────────────────────
# ──────────────────────────────────────────────

# Sidebar
with st.sidebar:
    st.markdown("## 🌾 AgriGuard")
    st.caption("Localized Climate Risk Prediction for Farmers")
    st.divider()

    crop_data = load_crop_data()
    city = st.text_input("📍 City / Town", placeholder="e.g. Chennai, Pune, Delhi",
                         value="Chennai")
    crop = st.selectbox("🌱 Crop", list(crop_data.keys()),
                        format_func=lambda x: x.capitalize())
    run  = st.button("🔍 Check Risk", use_container_width=True, type="primary")

    st.divider()
    st.caption("**How it works**")
    st.caption(
        "Fetches a 5-day / 3-hour forecast from OpenWeatherMap, "
        "aggregates to daily values, and computes crop-specific "
        "Heat · Drought · Flood · Pest risk levels."
    )

# Hero header
st.markdown(
    '<p class="hero-title">🌾 AgriGuard</p>'
    '<p class="hero-sub">Localized Climate Risk Prediction · Powered by OpenWeatherMap</p>',
    unsafe_allow_html=True
)
st.divider()

if not run:
    c1, c2, c3 = st.columns(3)
    c1.info("**📍 Step 1** — Enter your city in the sidebar")
    c2.info("**🌱 Step 2** — Select your crop")
    c3.info("**🔍 Step 3** — Click Check Risk")
    st.stop()

# ── Fetch & Process ──────────────────────────
with st.spinner("Fetching 5-day forecast…"):
    daily      = fetch_forecast(city.strip())
    thresholds = crop_data[crop]
    result     = apply_risks(daily, thresholds)

risk_type, severity = overall_risk(result)
advisory_text       = ADVISORY[risk_type]

# ── Summary metric tiles ─────────────────────
avg_tmax = daily["tmax"].mean()
avg_tmin = daily["tmin"].mean()
avg_hum  = daily["humidity"].mean()
tot_rain = daily["rainfall"].sum()

st.markdown(
    f"""<div class="metric-row">
      <div class="metric-tile"><div class="val">{avg_tmax:.1f}°C</div><div class="lbl">Avg Tmax</div></div>
      <div class="metric-tile"><div class="val">{avg_tmin:.1f}°C</div><div class="lbl">Avg Tmin</div></div>
      <div class="metric-tile"><div class="val">{avg_hum:.0f}%</div><div class="lbl">Avg Humidity</div></div>
      <div class="metric-tile"><div class="val">{tot_rain:.1f} mm</div><div class="lbl">Total Rainfall</div></div>
      <div class="metric-tile"><div class="val">{city.title()}</div><div class="lbl">Location</div></div>
      <div class="metric-tile"><div class="val">{crop.capitalize()}</div><div class="lbl">Crop</div></div>
    </div>""",
    unsafe_allow_html=True
)

# ── Two-column layout ─────────────────────────
left, right = st.columns([1.1, 1], gap="large")

with left:
    # ── Forecast Table ──────────────────────
    st.markdown('<p class="section-title">📊 5-Day Forecast & Risk Table</p>',
                unsafe_allow_html=True)

    rows_html = ""
    for _, row in result.iterrows():
        rows_html += (
            f"<tr>"
            f"<td>{row['date']}</td>"
            f"<td>{row['tmax']:.1f}</td>"
            f"<td>{row['tmin']:.1f}</td>"
            f"<td>{row['humidity']:.0f}</td>"
            f"<td>{row['rainfall']:.2f}</td>"
            f"<td>{badge(row['Heat'])}</td>"
            f"<td>{badge(row['Drought'])}</td>"
            f"<td>{badge(row['Flood'])}</td>"
            f"<td>{badge(row['Pest'])}</td>"
            f"</tr>"
        )

    st.markdown(f"""
<table class="forecast-table">
  <thead><tr>
    <th>Date</th><th>Tmax °C</th><th>Tmin °C</th>
    <th>Humidity %</th><th>Rain mm</th>
    <th>Heat</th><th>Drought</th><th>Flood</th><th>Pest</th>
  </tr></thead>
  <tbody>{rows_html}</tbody>
</table>""", unsafe_allow_html=True)

    # ── Overall Risk ────────────────────────
    st.markdown('<p class="section-title">⚠️ Overall Risk</p>', unsafe_allow_html=True)

    if severity == "None":
        css, icon, label = "risk-safe",   "✅", "No Major Risk Detected"
    elif severity == "High":
        css, icon, label = "risk-danger", "🚨", f"{risk_type} Risk — HIGH"
    else:
        css, icon, label = "risk-warn",   "⚠️", f"{risk_type} Risk — MEDIUM"

    st.markdown(f'<div class="risk-card {css}">{icon}&nbsp; {label}</div>',
                unsafe_allow_html=True)

    # ── Advisory ────────────────────────────
    st.markdown('<p class="section-title">🌿 Advisory</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="advisory">{advisory_text}</div>', unsafe_allow_html=True)

    # ── Crop thresholds ──────────────────────
    with st.expander("📋 Crop Thresholds Reference"):
        t = thresholds
        st.markdown(f"""
<table class="thresh-table">
  <tr><th>Parameter</th><th>Value</th></tr>
  <tr><td>Max Temperature</td><td>{t['tmax']} °C</td></tr>
  <tr><td>Min Temperature</td><td>{t['tmin']} °C</td></tr>
  <tr><td>Min Daily Rainfall</td><td>{t['min_rainfall']} mm/day</td></tr>
  <tr><td>Max Daily Rainfall</td><td>{t['max_rainfall']} mm/day</td></tr>
  <tr><td>Max Humidity</td><td>{t['humidity']} %</td></tr>
</table>""", unsafe_allow_html=True)

with right:
    st.markdown('<p class="section-title">📈 Visual Forecast</p>', unsafe_allow_html=True)
    st.plotly_chart(
        temp_chart(daily, thresholds["tmax"]),
        use_container_width=True
    )
    st.plotly_chart(
        rain_chart(daily, thresholds["min_rainfall"], thresholds["max_rainfall"]),
        use_container_width=True
    )
    st.plotly_chart(
        risk_heatmap(result),
        use_container_width=True
    )

# ── Footer ───────────────────────────────────
st.divider()
st.caption(
    f"AgriGuard Prototype · Data: OpenWeatherMap 5-day forecast · "
    f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
)
