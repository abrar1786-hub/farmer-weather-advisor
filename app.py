import streamlit as st
import requests
import pandas as pd
import json

# -------------------------------
# 🔑 API KEYS
# -------------------------------
OPENWEATHER_API_KEY = "aafce6cf9cd8393e103087fe9ca4f55a"
WEATHERAPI_KEY = "a8ac0e16da04492fa3f193535262203"

# -------------------------------
# 📍 GET LAT/LON
# -------------------------------
def get_lat_lon(city):
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={OPENWEATHER_API_KEY}"
    res = requests.get(url).json()
    if len(res) == 0:
        return None, None
    return res[0]["lat"], res[0]["lon"]

# -------------------------------
# 🌤️ OPENWEATHER DATA
# -------------------------------
def fetch_openweather(lat, lon):
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
    df = df.groupby("date").mean().reset_index()
    return df

# -------------------------------
# 🌦️ WEATHERAPI DATA
# -------------------------------
def fetch_weatherapi(city):
    url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHERAPI_KEY}&q={city}&days=7"
    res = requests.get(url).json()

    data = []
    for day in res["forecast"]["forecastday"]:
        data.append({
            "date": day["date"],
            "tmax": day["day"]["maxtemp_c"],
            "tmin": day["day"]["mintemp_c"],
            "humidity": day["day"]["avghumidity"],
            "rainfall": day["day"]["totalprecip_mm"]
        })

    return pd.DataFrame(data)

# -------------------------------
# 🔄 MERGE DATA
# -------------------------------
def merge_data(df1, df2):
    df = pd.merge(df1, df2, on="date", suffixes=("_ow", "_wa"))
    df["tmax"] = df[["tmax_ow", "tmax_wa"]].mean(axis=1)
    df["tmin"] = df[["tmin_ow", "tmin_wa"]].mean(axis=1)
    df["humidity"] = df[["humidity_ow", "humidity_wa"]].mean(axis=1)
    df["rainfall"] = df[["rainfall_ow", "rainfall_wa"]].mean(axis=1)
    return df[["date", "tmax", "tmin", "humidity", "rainfall"]]

# -------------------------------
# ⚠️ RISK CALCULATION (FIXED)
# -------------------------------
def calculate_risk(row, crop):

    heat = "Low"
    drought = "Low"
    flood = "Low"
    pest = "Low"

    # 🌡 Heat
    if row["tmax"] > crop["tmax"]:
        heat = "High"

    # 🌵 Drought (FIXED LOGIC)
    if row["rainfall"] < crop["min_rainfall"]:
        if row["tmax"] > crop["tmin"]:   # only when crop can grow
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
        return "🌱 Use drip irrigation and conserve water"
    elif risk == "Flood":
        return "🚜 Ensure proper drainage in field"
    elif risk == "Pest":
        return "🐛 Monitor crops and use pest control"
    return "✅ No major risk"

# -------------------------------
# 🖥️ UI
# -------------------------------
st.title("🌾 Farmer Climate Risk Advisor")

city = st.text_input("📍 Enter your city")
crop_name = st.selectbox("🌱 Select crop", ["rice", "wheat", "maize", "cotton"])

check = st.button("🔍 Check Risk")

if check:

    with open("crop_data.json") as f:
        crops = json.load(f)

    crop = crops[crop_name]

    lat, lon = get_lat_lon(city)

    if lat is None:
        st.error("❌ City not found")
    else:
        with st.spinner("Fetching data... ⏳"):

            ow = fetch_openweather(lat, lon)
            wa = fetch_weatherapi(city)

            if ow.empty or wa.empty:
                st.error("❌ Data fetch failed")
            else:
                df = merge_data(ow, wa)

                # -------------------------------
                # 🔥 MULTI-DAY RISK
                # -------------------------------
                all_risks = []

                for _, row in df.iterrows():
                    heat, drought, flood, pest = calculate_risk(row, crop)

                    all_risks.append({
                        "date": row["date"],
                        "Heat": heat,
                        "Drought": drought,
                        "Flood": flood,
                        "Pest": pest
                    })

                risk_df = pd.DataFrame(all_risks)

                final_df = pd.merge(df, risk_df, on="date")

                st.subheader("📊 Weather + Risk Forecast")
                st.dataframe(final_df)

                # -------------------------------
                # 🔴 OVERALL RISK
                # -------------------------------
                risk_count = {"Heat": 0, "Drought": 0, "Flood": 0, "Pest": 0}

                for _, row in risk_df.iterrows():
                    for r in risk_count:
                        if row[r] == "High":
                            risk_count[r] += 1

                major_risk = max(risk_count, key=risk_count.get)

                st.subheader("⚠️ Overall Risk")

                if risk_count[major_risk] > 0:
                    st.error(f"🚨 {major_risk} Risk Dominates in Next Days")
                else:
                    st.success("✅ No Major Risk")

                # -------------------------------
                # 🌿 ADVISORY
                # -------------------------------
                st.subheader("🌿 Advice for Farmers")
                st.info(get_advisory(major_risk))
