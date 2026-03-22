import streamlit as st
import requests
import pandas as pd
import json

# -------------------------------
# 🔑 API KEYS
# -------------------------------
OPENWEATHER_API_KEY = "aafce6cf9cd8393e103087fe9ca4f55a"
WEATHERAPI_KEY = "a8ac0e16da04492fa3f193535262203"

NASA_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# -------------------------------
# 📍 GET LAT/LON
# -------------------------------
def get_lat_lon(city):
    try:
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={OPENWEATHER_API_KEY}"
        res = requests.get(url).json()
        if len(res) == 0:
            return None, None
        return res[0]["lat"], res[0]["lon"]
    except:
        return None, None

# -------------------------------
# 🌤️ OPENWEATHER
# -------------------------------
def fetch_openweather(lat, lon):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        res = requests.get(url).json()

        data = []
        for item in res["list"]:
            data.append({
                "date": item["dt_txt"].split(" ")[0],
                "tmax": item["main"]["temp_max"],
                "tmin": item["main"]["temp_min"],
                "humidity": item["main"]["humidity"],
                "rainfall": item.get("rain", {}).get("3h", 0)
            })

        df = pd.DataFrame(data)
        return df.groupby("date").mean().reset_index()
    except:
        return pd.DataFrame()

# -------------------------------
# 🌦️ WEATHERAPI
# -------------------------------
def fetch_weatherapi(city):
    try:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHERAPI_KEY}&q={city}&days=7"
        res = requests.get(url).json()

        data = []
        for d in res["forecast"]["forecastday"]:
            data.append({
                "date": d["date"],
                "tmax": d["day"]["maxtemp_c"],
                "tmin": d["day"]["mintemp_c"],
                "humidity": d["day"]["avghumidity"],
                "rainfall": d["day"]["totalprecip_mm"]
            })

        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# -------------------------------
# ☀️ NASA BASELINE (SAFE)
# -------------------------------
def fetch_nasa(lat, lon):
    try:
        params = {
            "parameters": "T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M",
            "community": "AG",
            "longitude": lon,
            "latitude": lat,
            "start": "20000101",
            "end": "20201231",
            "format": "JSON"
        }

        res = requests.get(NASA_URL, params=params).json()
        p = res["properties"]["parameter"]

        df = pd.DataFrame({
            "tmax": list(p["T2M_MAX"].values()),
            "tmin": list(p["T2M_MIN"].values()),
            "rainfall": list(p["PRECTOTCORR"].values()),
            "humidity": list(p["RH2M"].values())
        })

        df["date"] = pd.date_range("2000-01-01", periods=len(df))
        df["month"] = df["date"].dt.month

        return df.groupby("month").mean().reset_index()

    except:
        # 🔥 fallback (no crash)
        return pd.DataFrame({
            "month": list(range(1,13)),
            "tmax": [30]*12,
            "tmin": [20]*12,
            "rainfall": [100]*12,
            "humidity": [60]*12
        })

# -------------------------------
# 🔄 MERGE
# -------------------------------
def merge_data(df1, df2):
    if df1.empty: return df2
    if df2.empty: return df1

    df = pd.merge(df1, df2, on="date", suffixes=("_ow", "_wa"))
    df["tmax"] = df[["tmax_ow","tmax_wa"]].mean(axis=1)
    df["tmin"] = df[["tmin_ow","tmin_wa"]].mean(axis=1)
    df["humidity"] = df[["humidity_ow","humidity_wa"]].mean(axis=1)
    df["rainfall"] = df[["rainfall_ow","rainfall_wa"]].mean(axis=1)

    return df[["date","tmax","tmin","humidity","rainfall"]]

# -------------------------------
# ⚠️ RISK (FINAL)
# -------------------------------
def calculate_risk(row, crop, base):

    heat = drought = flood = pest = "Low"

    # 🌡 Heat
    if row["tmax"] > crop["tmax"]:
        heat = "High"

    # 🌵 Drought (SMART)
    if row["rainfall"] < base["rainfall"] * 0.4:
        if row["tmax"] > 25:
            drought = "High"

    # 🌊 Flood
    if row["rainfall"] > crop["max_rainfall"]:
        flood = "High"

    # 🐛 Pest
    if row["humidity"] > crop["humidity"] and 15 <= row["tmin"] <= 25:
        pest = "High"

    return heat, drought, flood, pest

# -------------------------------
# 🌿 ADVISORY
# -------------------------------
def get_advisory(risk):
    if risk == "Heat":
        return "💧 Increase irrigation and avoid afternoon work"
    elif risk == "Drought":
        return "🌱 Use drip irrigation and conserve soil moisture"
    elif risk == "Flood":
        return "🚜 Ensure drainage and avoid water stagnation"
    elif risk == "Pest":
        return "🐛 Monitor crops and apply pest control"
    return "✅ Normal conditions"

# -------------------------------
# 🖥️ UI
# -------------------------------
st.title("🌾 Climate Risk Advisor")

city = st.text_input("📍 Enter City")
crop_name = st.selectbox("🌱 Crop", ["rice","wheat","maize","cotton"])

if st.button("🔍 Check Risk"):

    with open("crop_data.json") as f:
        crops = json.load(f)

    crop = crops[crop_name]

    lat, lon = get_lat_lon(city)

    if not lat:
        st.error("City not found")
    else:
        with st.spinner("Fetching data..."):

            ow = fetch_openweather(lat, lon)
            wa = fetch_weatherapi(city)
            base_df = fetch_nasa(lat, lon)

            df = merge_data(ow, wa)

            all_rows = []

            for _, row in df.iterrows():
                month = pd.to_datetime(row["date"]).month
                base = base_df[base_df["month"]==month].iloc[0]

                heat, drought, flood, pest = calculate_risk(row, crop, base)

                all_rows.append({
    "date": row["date"],
    "tmax": round(row["tmax"], 2),
    "tmin": round(row["tmin"], 2),   # ✅ ADD THIS LINE
    "rainfall": round(row["rainfall"], 2),
    "humidity": round(row["humidity"], 2),  # (optional but useful)

    "Heat": heat,
    "Drought": drought,
    "Flood": flood,
    "Pest": pest
})

            final = pd.DataFrame(all_rows)

            st.dataframe(final)

            # overall risk
            counts = {"Heat":0,"Drought":0,"Flood":0,"Pest":0}
            for _, r in final.iterrows():
                for k in counts:
                    if r[k]=="High":
                        counts[k]+=1

            if all(v==0 for v in counts.values()):
                major = "None"
            else:
                major = max(counts, key=counts.get)

            st.subheader("⚠️ Overall Risk")

            if major=="None":
                st.success("No major risk")
            else:
                st.error(f"{major} Risk Detected")

            st.subheader("🌿 Advisory")
            st.info(get_advisory(major))
