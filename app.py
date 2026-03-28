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

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #f9fafb;
}

/* ── Brand header ── */
.brand {
    text-align: center;
    padding: 32px 0 8px 0;
}
.brand-title {
    font-size: 2rem;
    font-weight: 700;
    color: #14532d;
    letter-spacing: -0.5px;
}
.brand-sub {
    font-size: 0.88rem;
    color: #6b7280;
    margin-top: 4px;
}

/* ── Main risk card ── */
.main-card {
    border-radius: 20px;
    padding: 36px 32px;
    text-align: center;
    margin: 24px 0 16px 0;
    box-shadow: 0 2px 16px rgba(0,0,0,0.07);
}
.card-danger { background: #fff1f2; border: 1.5px solid #fca5a5; }
.card-warn   { background: #fffbeb; border: 1.5px solid #fcd34d; }
.card-safe   { background: #f0fdf4; border: 1.5px solid #86efac; }

.card-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 10px;
}
.label-danger { color: #dc2626; }
.label-warn   { color: #d97706; }
.label-safe   { color: #16a34a; }

.card-risk {
    font-size: 2.2rem;
    font-weight: 700;
    line-height: 1.15;
    margin-bottom: 6px;
}
.text-danger { color: #b91c1c; }
.text-warn   { color: #b45309; }
.text-safe   { color: #15803d; }

.card-city {
    font-size: 0.9rem;
    color: #6b7280;
    margin-bottom: 20px;
}

.advisory-text {
    font-size: 0.95rem;
    color: #374151;
    line-height: 1.7;
    background: rgba(255,255,255,0.7);
    border-radius: 12px;
    padding: 14px 18px;
    margin-top: 4px;
    text-align: left;
}

/* ── Risk pills row ── */
.pills-row {
    display: flex;
    gap: 10px;
    justify-content: center;
    flex-wrap: wrap;
    margin: 0 0 8px 0;
}
.pill {
    display: flex;
    flex-direction: column;
    align-items: center;
    border-radius: 14px;
    padding: 10px 20px;
    min-width: 80px;
    font-size: 0.8rem;
    font-weight: 500;
    color: #374151;
    background: #fff;
    border: 1px solid #e5e7eb;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.pill-icon { font-size: 1.3rem; margin-bottom: 4px; }
.pill-name { font-size: 0.7rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.5px; }
.pill-high   { border-color: #fca5a5; background: #fff1f2; color: #b91c1c; }
.pill-medium { border-color: #fcd34d; background: #fffbeb; color: #b45309; }
.pill-low    { border-color: #86efac; background: #f0fdf4; color: #15803d; }

/* ── Details expander ── */
.details-toggle {
    text-align: center;
    color: #6b7280;
    font-size: 0.85rem;
    cursor: pointer;
    margin: 8px 0 0 0;
}

/* ── Forecast table ── */
.ft { width:100%; border-collapse:collapse; font-size:0.84rem; }
.ft th {
    background: #14532d; color: #fff;
    padding: 10px 12px; text-align:center; font-weight:600;
    font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.5px;
}
.ft td { padding:9px 12px; border-bottom:1px solid #f3f4f6; text-align:center; color:#374151; }
.ft tr:last-child td { border-bottom:none; }
.ft tr:nth-child(even) td { background:#fafafa; }

.badge {
    display:inline-block; padding:3px 10px;
    border-radius:20px; font-size:0.75rem; font-weight:600;
}
.badge-High   { background:#fee2e2; color:#b91c1c; }
.badge-Medium { background:#fef3c7; color:#b45309; }
.badge-Low    { background:#dcfce7; color:#15803d; }

/* ── Footer ── */
.footer {
    text-align: center;
    font-size: 0.75rem;
    color: #9ca3af;
    padding: 24px 0 8px 0;
}

/* Hide streamlit default elements */
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 0 !important; }
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
        st.error(f"❌ City **'{city}'** not found.")
        st.stop()
    if resp.status_code != 200:
        st.error(f"❌ API error {resp.status_code}")
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
          .agg(tmax=("tmax","max"), tmin=("tmin","min"),
               humidity=("humidity","mean"), rainfall=("rainfall","sum"))
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
def heat_risk(tmax, crop_tmax):
    if tmax > crop_tmax:           return "High"
    if tmax >= crop_tmax - 3:      return "Medium"
    return "Low"

def drought_risk(rainfall, min_rain):
    if rainfall < min_rain:        return "High"
    if rainfall <= min_rain + 10:  return "Medium"
    return "Low"

def flood_risk(rainfall, max_rain):
    if rainfall == 0.0:            return "Low"
    if rainfall > max_rain:        return "High"
    if rainfall >= max_rain - 10:  return "Medium"
    return "Low"

def pest_risk(humidity, tmin, crop_hum):
    if tmin < 10.0:                return "Low"
    if humidity > crop_hum:        return "High"
    if humidity >= crop_hum - 10:  return "Medium"
    return "Low"

def apply_risks(daily, thresholds):
    df = daily.copy()
    df["Heat"]    = df.apply(lambda r: heat_risk(r["tmax"], thresholds["tmax"]), axis=1)
    df["Drought"] = df.apply(lambda r: drought_risk(r["rainfall"], thresholds["min_rainfall"]), axis=1)
    df["Flood"]   = df.apply(lambda r: flood_risk(r["rainfall"], thresholds["max_rainfall"]), axis=1)
    df["Pest"]    = df.apply(lambda r: pest_risk(r["humidity"], r["tmin"], thresholds["humidity"]), axis=1)
    return df

PRIORITY = ["Heat", "Drought", "Flood", "Pest"]

def overall_risk(df):
    for col in PRIORITY:
        if (df[col] == "High").any():   return col, "High"
    for col in PRIORITY:
        if (df[col] == "Medium").any(): return col, "Medium"
    return "No major risk", "None"

# ─────────────────────────────────────────────
# ADVISORY  (clean plain text)
# ─────────────────────────────────────────────
ADVISORY = {
    "Heat":         "Temperatures are too high for your crop. Avoid fieldwork between 11 AM – 3 PM. Water your crops more frequently and use shade covers if possible.",
    "Drought":      "Not enough rain expected this week. Use drip irrigation to conserve water. Avoid tilling the soil so moisture doesn't evaporate.",
    "Flood":        "Heavy rain expected. Make sure drainage channels are clear. Do not apply fertilizer before rain — it will wash away.",
    "Pest":         "High humidity may bring pests and fungal disease. Check your crops every 2 days. Apply preventive pesticide or fungicide spray.",
    "No major risk": "Weather looks good for your crop this week. Continue normal farming. Check again tomorrow for updates.",
}

RISK_ICON = {
    "Heat":  "🌡️", "Drought": "🌵", "Flood": "🌊",
    "Pest":  "🐛", "No major risk": "✅",
}
PILL_ICON = {"Heat": "🔥", "Drought": "💧", "Flood": "🌊", "Pest": "🐛"}

# ─────────────────────────────────────────────
# CHARTS  (details panel)
# ─────────────────────────────────────────────
def temp_chart(df, crop_tmax):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["tmax"], mode="lines+markers",
        name="Max °C", line=dict(color="#dc2626", width=2.5), marker=dict(size=7)))
    fig.add_trace(go.Scatter(x=df["date"], y=df["tmin"], mode="lines+markers",
        name="Min °C", line=dict(color="#2563eb", width=2.5), marker=dict(size=7),
        fill="tonexty", fillcolor="rgba(147,197,253,0.15)"))
    fig.add_hline(y=crop_tmax, line_dash="dot", line_color="#dc2626",
        annotation_text=f"Crop limit {crop_tmax}°C", annotation_font_size=11)
    fig.update_layout(
        title="Temperature Forecast", xaxis_title="Date", yaxis_title="°C",
        height=280, margin=dict(l=0,r=0,t=36,b=0),
        legend=dict(orientation="h", y=-0.3),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=12, color="#374151"),
        xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#f3f4f6"),
    )
    return fig

def rain_chart(df, min_rain, max_rain):
    fig = go.Figure(go.Bar(x=df["date"], y=df["rainfall"],
        marker_color="#16a34a", marker_line_color="#14532d", marker_line_width=1))
    fig.add_hline(y=min_rain, line_dash="dot", line_color="#d97706",
        annotation_text=f"Min {min_rain}mm", annotation_font_size=11)
    if max_rain < 50:
        fig.add_hline(y=max_rain, line_dash="dot", line_color="#dc2626",
            annotation_text=f"Max {max_rain}mm", annotation_font_size=11)
    fig.update_layout(
        title="Rainfall Forecast", xaxis_title="Date", yaxis_title="mm",
        height=260, margin=dict(l=0,r=0,t=36,b=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=12, color="#374151"),
        xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#f3f4f6"),
    )
    return fig

def badge(val):
    return f'<span class="badge badge-{val}">{val}</span>'

# ─────────────────────────────────────────────
# ─── UI ──────────────────────────────────────
# ─────────────────────────────────────────────
crop_data = load_crop_data()

# Brand header
st.markdown("""
<div class="brand">
  <div class="brand-title">🌾 AgriGuard</div>
  <div class="brand-sub">Climate Risk Advisor for Farmers</div>
</div>
""", unsafe_allow_html=True)

# Input row
c1, c2 = st.columns([2, 1])
with c1:
    city = st.text_input("", placeholder="Enter your city  (e.g. Chennai, Pune)",
                         label_visibility="collapsed")
with c2:
    crop = st.selectbox("", list(crop_data.keys()),
                        format_func=lambda x: x.capitalize(),
                        label_visibility="collapsed")

run = st.button("Check Risk →", use_container_width=True, type="primary")

# ─── Landing state ───────────────────────────
if not run:
    st.markdown("""
    <div style="text-align:center; color:#9ca3af; padding:40px 0; font-size:0.9rem;">
        Enter your city and crop above, then tap <b>Check Risk</b>
    </div>""", unsafe_allow_html=True)
    st.stop()

if not city.strip():
    st.warning("Please enter a city name.")
    st.stop()

# ─── Fetch & compute ─────────────────────────
with st.spinner("Checking weather…"):
    daily      = fetch_forecast(city.strip())
    thresholds = crop_data[crop]
    result     = apply_risks(daily, thresholds)

risk_type, severity = overall_risk(result)

# ─── Main risk card ───────────────────────────
if severity == "None":
    card_css   = "card-safe"
    label_css  = "label-safe"
    text_css   = "text-safe"
    label_text = "ALL CLEAR"
elif severity == "High":
    card_css   = "card-danger"
    label_css  = "label-danger"
    text_css   = "text-danger"
    label_text = "RISK DETECTED"
else:
    card_css   = "card-warn"
    label_css  = "label-warn"
    text_css   = "text-warn"
    label_text = "CAUTION"

icon    = RISK_ICON[risk_type]
adv     = ADVISORY[risk_type]
display = "No Major Risk" if risk_type == "No major risk" else f"{risk_type} Risk"

st.markdown(f"""
<div class="main-card {card_css}">
  <div class="card-label {label_css}">{label_text}</div>
  <div class="card-risk {text_css}">{icon} {display}</div>
  <div class="card-city">{city.title()} · {crop.capitalize()} · Next 5 Days</div>
  <div class="advisory-text">{adv}</div>
</div>
""", unsafe_allow_html=True)

# ─── 4 risk pills ────────────────────────────
def pill_css(val):
    return f"pill pill-{val.lower()}"

day_risks = {
    "Heat":    result["Heat"].mode()[0],
    "Drought": result["Drought"].mode()[0],
    "Flood":   result["Flood"].mode()[0],
    "Pest":    result["Pest"].mode()[0],
}

pills_html = '<div class="pills-row">'
for name, val in day_risks.items():
    pills_html += f"""
    <div class="{pill_css(val)}">
      <span class="pill-icon">{PILL_ICON[name]}</span>
      <span>{val}</span>
      <span class="pill-name">{name}</span>
    </div>"""
pills_html += "</div>"
st.markdown(pills_html, unsafe_allow_html=True)

# ─── Details expander ────────────────────────
with st.expander("📋 View detailed forecast & charts"):

    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(temp_chart(daily, thresholds["tmax"]), use_container_width=True)
    with col2:
        st.plotly_chart(rain_chart(daily, thresholds["min_rainfall"], thresholds["max_rainfall"]),
                        use_container_width=True)

    # Table
    st.markdown("**5-Day Risk Breakdown**")
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

    # Crop thresholds
    st.markdown("**Crop Thresholds Used**")
    t = thresholds
    st.markdown(f"""
| Parameter | Value |
|---|---|
| Max Temperature | {t['tmax']} °C |
| Min Daily Rainfall | {t['min_rainfall']} mm |
| Max Daily Rainfall | {t['max_rainfall']} mm |
| Max Humidity | {t['humidity']} % |
""")

# ─── Footer ──────────────────────────────────
st.markdown(
    f'<div class="footer">AgriGuard Prototype · '
    f'OpenWeatherMap · {datetime.now().strftime("%d %b %Y")}</div>',
    unsafe_allow_html=True
)
