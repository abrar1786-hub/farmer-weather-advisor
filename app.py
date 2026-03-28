import streamlit as st
import requests
import pandas as pd
import json
import plotly.graph_objects as go
from datetime import datetime

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AgriGuard",
    page_icon="🌾",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

*, html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    color: inherit;
}

body { background-color: #f9fafb; }
.block-container { padding-top: 0 !important; max-width: 720px; }
#MainMenu, footer, header { visibility: hidden; }

/* ── Brand ── */
.brand {
    text-align: center;
    padding: 32px 0 16px 0;
}
.brand-title {
    font-size: 1.9rem;
    font-weight: 700;
    color: #14532d;
    letter-spacing: -0.5px;
}
.brand-sub {
    font-size: 0.85rem;
    color: #6b7280;
    margin-top: 4px;
    font-weight: 400;
}

/* ── Main risk card ── */
.main-card {
    border-radius: 20px;
    padding: 32px 28px;
    text-align: center;
    margin: 20px 0 14px 0;
    box-shadow: 0 2px 16px rgba(0,0,0,0.06);
}
.card-danger { background:#fff1f2; border:1.5px solid #fca5a5; }
.card-warn   { background:#fffbeb; border:1.5px solid #fcd34d; }
.card-safe   { background:#f0fdf4; border:1.5px solid #86efac; }

.card-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 10px;
}
.label-danger { color: #dc2626; }
.label-warn   { color: #d97706; }
.label-safe   { color: #16a34a; }

.card-risk {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 6px;
}
.text-danger { color: #b91c1c; }
.text-warn   { color: #b45309; }
.text-safe   { color: #15803d; }

.card-city {
    font-size: 0.85rem;
    color: #6b7280;
    font-weight: 400;
    margin-bottom: 18px;
}

.advisory-text {
    font-size: 0.93rem;
    color: #1f2937;
    font-weight: 400;
    line-height: 1.75;
    background: rgba(255,255,255,0.75);
    border-radius: 12px;
    padding: 14px 16px;
    text-align: left;
}

/* ── Risk pills ── */
.pills-row {
    display: flex;
    gap: 10px;
    justify-content: center;
    flex-wrap: wrap;
    margin: 4px 0 6px 0;
}
.pill {
    display: flex;
    flex-direction: column;
    align-items: center;
    border-radius: 14px;
    padding: 10px 22px;
    min-width: 86px;
    background: #fff;
    border: 1.5px solid #e5e7eb;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.pill-icon  { font-size: 1.3rem; margin-bottom: 4px; }
.pill-val   { font-size: 0.82rem; font-weight: 600; }
.pill-name  { font-size: 0.68rem; color: #9ca3af; text-transform: uppercase;
               letter-spacing: 0.5px; margin-top: 2px; font-weight: 500; }

.pill-high   { border-color: #fca5a5; background:#fff1f2; }
.pill-high   .pill-val { color: #b91c1c; }

.pill-medium { border-color: #fcd34d; background:#fffbeb; }
.pill-medium .pill-val { color: #b45309; }

.pill-low    { border-color: #86efac; background:#f0fdf4; }
.pill-low    .pill-val { color: #15803d; }

/* ── Forecast table ── */
.ft {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.83rem;
    border-radius: 12px;
    overflow: hidden;
}
.ft th {
    background: #14532d;
    color: #ffffff;
    padding: 10px 10px;
    text-align: center;
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}
.ft td {
    padding: 9px 10px;
    border-bottom: 1px solid #f3f4f6;
    text-align: center;
    color: #1f2937;
    font-weight: 400;
    font-size: 0.83rem;
    background: #ffffff;
}
.ft tr:nth-child(even) td { background: #f9fafb; }
.ft tr:last-child td { border-bottom: none; }

/* ── Badges ── */
.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    line-height: 1;
}
.badge-High   { background: #fee2e2; color: #b91c1c; }
.badge-Medium { background: #fef3c7; color: #b45309; }
.badge-Low    { background: #dcfce7; color: #15803d; }

/* ── Threshold table ── */
.thresh-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.84rem;
    margin-top: 4px;
}
.thresh-table th {
    background: #f3f4f6;
    color: #374151;
    padding: 9px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.thresh-table td {
    padding: 8px 12px;
    border-bottom: 1px solid #f3f4f6;
    color: #1f2937;
    font-weight: 400;
}
.thresh-table tr:last-child td { border-bottom: none; }

/* ── Section label ── */
.section-label {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #6b7280;
    margin: 20px 0 10px 0;
}

/* ── Footer ── */
.footer {
    text-align: center;
    font-size: 0.73rem;
    color: #9ca3af;
    padding: 20px 0 8px 0;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# API KEY
# ─────────────────────────────────────────────
try:
    API_KEY = st.secrets["OPENWEATHER_API_KEY"]
except Exception:
    API_KEY = "aafce6cf9cd8393e103087fe9ca4f55a"

# ─────────────────────────────────────────────
# LOAD CROP DATA
# ─────────────────────────────────────────────
@st.cache_data
def load_crop_data():
    with open("crop_data.json") as f:
        return json.load(f)

# ─────────────────────────────────────────────
# FETCH WEATHER
# ─────────────────────────────────────────────
def fetch_forecast(city: str) -> pd.DataFrame:
    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        f"?q={city}&appid={API_KEY}&units=metric"
    )
    try:
        resp = requests.get(url, timeout=12)
    except requests.exceptions.ConnectionError:
        st.error("❌ Network error. Check your connection.")
        st.stop()
    except requests.exceptions.Timeout:
        st.error("❌ Request timed out. Try again.")
        st.stop()

    if resp.status_code == 401:
        st.error("❌ Invalid API key.")
        st.stop()
    if resp.status_code == 404:
        st.error(f"❌ City **'{city}'** not found. Check spelling.")
        st.stop()
    if resp.status_code != 200:
        st.error(f"❌ Weather API error ({resp.status_code}).")
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
          .agg(tmax=("tmax", "max"), tmin=("tmin", "min"),
               humidity=("humidity", "mean"), rainfall=("rainfall", "sum"))
          .reset_index()
    )
    daily["tmax"]     = daily["tmax"].round(1)
    daily["tmin"]     = daily["tmin"].round(1)
    daily["humidity"] = daily["humidity"].round(1)
    daily["rainfall"] = daily["rainfall"].round(2)
    return daily.head(5).copy()

# ─────────────────────────────────────────────
# RISK LOGIC
# ─────────────────────────────────────────────
def heat_risk(tmax: float, crop_tmax: float) -> str:
    if tmax > crop_tmax:
        return "High"
    if tmax >= crop_tmax - 3:
        return "Medium"
    return "Low"


def drought_risk(rainfall: float, min_rain: float) -> str:
    if rainfall < min_rain:
        return "High"
    if rainfall <= min_rain + 10:
        return "Medium"
    return "Low"


def flood_risk(rainfall: float, max_rain: float) -> str:
    """
    High   : rainfall clearly exceeds crop max
    Medium : rainfall is between 80–100% of crop max  (genuinely concerning)
    Low    : anything below 80% of max, including zero
    """
    if rainfall <= 0.0:
        return "Low"
    if rainfall > max_rain:
        return "High"
    if rainfall >= max_rain * 0.80:   # only top 20% of safe range → Medium
        return "Medium"
    return "Low"


def pest_risk(humidity: float, tmin: float, crop_hum: float) -> str:
    """
    Pest activity is negligible below 10 °C.
    High   : humidity clearly exceeds crop threshold
    Medium : humidity within 10 % below crop threshold
    Low    : otherwise
    """
    if tmin < 10.0:
        return "Low"
    if humidity > crop_hum:
        return "High"
    if humidity >= crop_hum - 10:
        return "Medium"
    return "Low"


def apply_risks(daily: pd.DataFrame, thresholds: dict) -> pd.DataFrame:
    df = daily.copy()
    df["Heat"]    = df.apply(lambda r: heat_risk(r["tmax"],     thresholds["tmax"]),         axis=1)
    df["Drought"] = df.apply(lambda r: drought_risk(r["rainfall"], thresholds["min_rainfall"]), axis=1)
    df["Flood"]   = df.apply(lambda r: flood_risk(r["rainfall"],   thresholds["max_rainfall"]), axis=1)
    df["Pest"]    = df.apply(lambda r: pest_risk(r["humidity"],  r["tmin"], thresholds["humidity"]), axis=1)
    return df


PRIORITY = ["Heat", "Drought", "Flood", "Pest"]

def overall_risk(df: pd.DataFrame):
    for col in PRIORITY:
        if (df[col] == "High").any():
            return col, "High"
    for col in PRIORITY:
        if (df[col] == "Medium").any():
            return col, "Medium"
    return "No major risk", "None"

# ─────────────────────────────────────────────
# ADVISORY
# ─────────────────────────────────────────────
ADVISORY = {
    "Heat":
        "Temperatures are exceeding safe limits for your crop. "
        "Avoid working in the field between 11 AM – 3 PM. "
        "Water your crops more frequently and use shade covers if possible.",
    "Drought":
        "Rainfall is below what your crop needs this week. "
        "Switch to drip or sprinkler irrigation to conserve water. "
        "Avoid tilling the soil so that moisture does not evaporate.",
    "Flood":
        "Heavy rainfall is expected above safe levels for your crop. "
        "Clear your drainage channels now. "
        "Do not apply fertilizer before the rain — it will wash away.",
    "Pest":
        "High humidity is creating conditions for pests and fungal disease. "
        "Check your crops every 2 days. "
        "Apply a preventive pesticide or fungicide spray as soon as possible.",
    "No major risk":
        "Weather looks good for your crop this week. "
        "Continue your normal farming routine. "
        "Check again tomorrow for any changes.",
}

RISK_ICON = {
    "Heat": "🌡️", "Drought": "🌵", "Flood": "🌊",
    "Pest": "🐛",  "No major risk": "✅",
}
PILL_ICON = {"Heat": "🔥", "Drought": "💧", "Flood": "🌊", "Pest": "🐛"}

# ─────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────
CHART_FONT = dict(family="Inter", size=12, color="#374151")

def temp_chart(df: pd.DataFrame, crop_tmax: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["tmax"], mode="lines+markers",
        name="Max °C",
        line=dict(color="#dc2626", width=2.5),
        marker=dict(size=7, color="#dc2626")
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["tmin"], mode="lines+markers",
        name="Min °C",
        line=dict(color="#2563eb", width=2.5),
        marker=dict(size=7, color="#2563eb"),
        fill="tonexty", fillcolor="rgba(147,197,253,0.15)"
    ))
    fig.add_hline(
        y=crop_tmax, line_dash="dot", line_color="#dc2626", line_width=1.5,
        annotation_text=f"Crop limit {crop_tmax}°C",
        annotation_font=dict(size=11, color="#dc2626"),
        annotation_position="top left"
    )
    fig.update_layout(
        title=dict(text="Temperature Forecast", font=dict(size=13, color="#111827")),
        xaxis_title="", yaxis_title="°C",
        height=270, margin=dict(l=0, r=0, t=36, b=0),
        legend=dict(orientation="h", y=-0.3, font=dict(color="#374151")),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=CHART_FONT,
        xaxis=dict(showgrid=False, tickfont=dict(color="#374151")),
        yaxis=dict(gridcolor="#f3f4f6", tickfont=dict(color="#374151")),
    )
    return fig


def rain_chart(df: pd.DataFrame, min_rain: float, max_rain: float) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=df["date"], y=df["rainfall"],
        marker_color="#16a34a",
        marker_line_color="#14532d",
        marker_line_width=1,
        name="Rainfall mm"
    ))
    fig.add_hline(
        y=min_rain, line_dash="dot", line_color="#d97706", line_width=1.5,
        annotation_text=f"Min {min_rain}mm",
        annotation_font=dict(size=11, color="#d97706"),
        annotation_position="top left"
    )
    fig.add_hline(
        y=max_rain, line_dash="dot", line_color="#dc2626", line_width=1.5,
        annotation_text=f"Max {max_rain}mm",
        annotation_font=dict(size=11, color="#dc2626"),
        annotation_position="top right"
    )
    fig.update_layout(
        title=dict(text="Rainfall Forecast", font=dict(size=13, color="#111827")),
        xaxis_title="", yaxis_title="mm",
        height=250, margin=dict(l=0, r=0, t=36, b=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=CHART_FONT,
        xaxis=dict(showgrid=False, tickfont=dict(color="#374151")),
        yaxis=dict(gridcolor="#f3f4f6", tickfont=dict(color="#374151")),
        showlegend=False,
    )
    return fig

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def badge(val: str) -> str:
    return f'<span class="badge badge-{val}">{val}</span>'

def pill_block(name: str, val: str) -> str:
    return f"""
    <div class="pill pill-{val.lower()}">
      <span class="pill-icon">{PILL_ICON[name]}</span>
      <span class="pill-val">{val}</span>
      <span class="pill-name">{name}</span>
    </div>"""

# ─────────────────────────────────────────────
# ─── UI ──────────────────────────────────────
# ─────────────────────────────────────────────
crop_data = load_crop_data()

# Brand
st.markdown("""
<div class="brand">
  <div class="brand-title">🌾 AgriGuard</div>
  <div class="brand-sub">Climate Risk Advisor for Farmers</div>
</div>
""", unsafe_allow_html=True)

# Inputs
c1, c2 = st.columns([2, 1])
with c1:
    city = st.text_input("", placeholder="Enter your city (e.g. Chennai, Pune)",
                         label_visibility="collapsed")
with c2:
    crop = st.selectbox("", list(crop_data.keys()),
                        format_func=lambda x: x.capitalize(),
                        label_visibility="collapsed")

run = st.button("Check Risk →", use_container_width=True, type="primary")

# Landing
if not run:
    st.markdown("""
    <div style="text-align:center; color:#9ca3af; padding:48px 0; font-size:0.88rem; font-weight:400;">
        Enter your city and crop above, then tap <b style="color:#6b7280;">Check Risk</b>
    </div>""", unsafe_allow_html=True)
    st.stop()

if not city.strip():
    st.warning("Please enter a city name.")
    st.stop()

# Fetch & compute
with st.spinner("Checking weather…"):
    daily      = fetch_forecast(city.strip())
    thresholds = crop_data[crop]
    result     = apply_risks(daily, thresholds)

risk_type, severity = overall_risk(result)

# Card styling
if severity == "None":
    card_css, label_css, text_css = "card-safe",   "label-safe",   "text-safe"
    label_text = "ALL CLEAR"
elif severity == "High":
    card_css, label_css, text_css = "card-danger", "label-danger", "text-danger"
    label_text = "RISK DETECTED"
else:
    card_css, label_css, text_css = "card-warn",   "label-warn",   "text-warn"
    label_text = "CAUTION"

display = "No Major Risk" if risk_type == "No major risk" else f"{risk_type} Risk"

# ── Main card ────────────────────────────────
st.markdown(f"""
<div class="main-card {card_css}">
  <div class="card-label {label_css}">{label_text}</div>
  <div class="card-risk  {text_css}">{RISK_ICON[risk_type]} {display}</div>
  <div class="card-city">{city.title()} &middot; {crop.capitalize()} &middot; Next 5 Days</div>
  <div class="advisory-text">{ADVISORY[risk_type]}</div>
</div>
""", unsafe_allow_html=True)

# ── 4 risk pills ─────────────────────────────
# Use mode (most-frequent value over 5 days) per risk type
day_risks = {col: result[col].mode()[0] for col in PRIORITY}

pills_html = '<div class="pills-row">'
for name in PRIORITY:
    pills_html += pill_block(name, day_risks[name])
pills_html += "</div>"
st.markdown(pills_html, unsafe_allow_html=True)

# ── Details expander ─────────────────────────
with st.expander("📋 View detailed forecast & charts"):

    # Charts side by side
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            temp_chart(daily, thresholds["tmax"]),
            use_container_width=True
        )
    with col2:
        st.plotly_chart(
            rain_chart(daily, thresholds["min_rainfall"], thresholds["max_rainfall"]),
            use_container_width=True
        )

    # Table
    st.markdown('<div class="section-label">5-Day Risk Breakdown</div>',
                unsafe_allow_html=True)

    rows_html = ""
    for _, row in result.iterrows():
        rows_html += (
            f"<tr>"
            f"<td>{row['date']}</td>"
            f"<td>{row['tmax']:.1f}°C</td>"
            f"<td>{row['tmin']:.1f}°C</td>"
            f"<td>{row['humidity']:.0f}%</td>"
            f"<td>{row['rainfall']:.1f}mm</td>"
            f"<td>{badge(row['Heat'])}</td>"
            f"<td>{badge(row['Drought'])}</td>"
            f"<td>{badge(row['Flood'])}</td>"
            f"<td>{badge(row['Pest'])}</td>"
            f"</tr>"
        )

    st.markdown(f"""
<table class="ft">
  <thead><tr>
    <th>Date</th><th>Tmax</th><th>Tmin</th>
    <th>Humidity</th><th>Rain</th>
    <th>Heat</th><th>Drought</th><th>Flood</th><th>Pest</th>
  </tr></thead>
  <tbody>{rows_html}</tbody>
</table>""", unsafe_allow_html=True)

    # Thresholds
    st.markdown('<div class="section-label" style="margin-top:20px;">Crop Thresholds</div>',
                unsafe_allow_html=True)
    t = thresholds
    st.markdown(f"""
<table class="thresh-table">
  <thead><tr><th>Parameter</th><th>Value</th></tr></thead>
  <tbody>
    <tr><td>Max Temperature</td><td>{t['tmax']} °C</td></tr>
    <tr><td>Min Daily Rainfall</td><td>{t['min_rainfall']} mm</td></tr>
    <tr><td>Max Daily Rainfall</td><td>{t['max_rainfall']} mm</td></tr>
    <tr><td>Max Humidity</td><td>{t['humidity']} %</td></tr>
  </tbody>
</table>""", unsafe_allow_html=True)

# ── Footer ───────────────────────────────────
st.markdown(
    f'<div class="footer">AgriGuard &middot; OpenWeatherMap &middot; '
    f'{datetime.now().strftime("%d %b %Y")}</div>',
    unsafe_allow_html=True
)
