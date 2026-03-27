import streamlit as st
import requests
import pandas as pd
import json

# ---------------- CONFIG ----------------
API_KEY = "aafce6cf9cd8393e103087fe9ca4f55a"

# ---------------- LOAD CROP DATA ----------------
def load_crop_data():
    with open("crop_data.json") as f:
        return json.load(f)

# ---------------- GET LAT LON ----------------
def get_location(city):
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={API_KEY}"
    res = requests.get(url).json()
    if not res:
        return None, None
    return res[0]["lat"], res[0]["lon"]

# ---------------- GET WEATHER ----------------
def get_weather(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    data = requests.get(url).json()

    daily = {}

    for item in data["list"]:
        date = item["dt_txt"].split(" ")[0]

        temp = item["main"]["temp"]
        humidity = item["main"]["humidity"]
        rain = item.get("rain", {}).get("3h", 0)

        if date not in daily:
            daily[date] = {
                "tmax": temp,
                "tmin": temp,
                "humidity": humidity,
                "rainfall": rain
            }
        else:
            daily[date]["tmax"] = max(daily[date]["tmax"], temp)
            daily[date]["tmin"] = min(daily[date]["tmin"], temp)
            daily[date]["humidity"] = (daily[date]["humidity"] + humidity) / 2
            daily[date]["rainfall"] += rain

    df = pd.DataFrame(daily).T.reset_index()
    df.columns = ["date", "tmax", "tmin", "humidity", "rainfall"]

    return df.head(5)

# ---------------- FIXED RISK LOGIC ----------------
def analyze_risk(row, crop):
    # HEAT
    if row["tmax"] > crop["tmax"]:
        heat = "High"
    elif row["tmax"] >= crop["tmax"] - 3:
        heat = "Medium"
    else:
        heat = "Low"

    # DROUGHT
    if row["rainfall"] < crop["min_rainfall"]:
        drought = "High"
    elif row["rainfall"] <= crop["min_rainfall"] + 10:
        drought = "Medium"
    else:
        drought = "Low"

    # FLOOD
    if row["rainfall"] > crop["max_rainfall"]:
        flood = "High"
    elif row["rainfall"] >= crop["max_rainfall"] - 10:
        flood = "Medium"
    else:
        flood = "Low"

    # PEST (humidity-based)
    if row["humidity"] > crop["humidity"]:
        pest = "High"
    elif row["humidity"] >= crop["humidity"] - 10:
        pest = "Medium"
    else:
        pest = "Low"

    return heat, drought, flood, pest

# ---------------- OVERALL RISK ----------------
def get_overall(df):
    if "High" in df["Heat"].values:
        return "🔥 Heat Risk Detected"
    if "High" in df["Drought"].values:
        return "🌵 Drought Risk Detected"
    if "High" in df["Flood"].values:
        return "🌧 Flood Risk Detected"
    if "High" in df["Pest"].values:
        return "🐛 Pest Risk Detected"
    return "✅ No major risk"

# ---------------- ADVISORY ----------------
def get_advice(risk):
    if "Heat" in risk:
        return "Avoid afternoon work & irrigate crops"
    elif "Drought" in risk:
        return "Use drip irrigation and conserve water"
    elif "Flood" in risk:
        return "Ensure proper drainage to avoid waterlogging"
    elif "Pest" in risk:
        return "Monitor crops and apply pest control"
    else:
        return "Normal conditions. Continue routine farming"

# ---------------- UI ----------------
st.title("🌾 Farmer Climate Risk Advisor")

city = st.text_input("Enter your city")
crop_name = st.selectbox("Select crop", ["rice", "wheat", "maize", "cotton"])

if st.button("🔍 Check Risk"):
    crop_data = load_crop_data()

    lat, lon = get_location(city)

    if lat is None:
        st.error("❌ Invalid city")
    else:
        df = get_weather(lat, lon)

        crop = crop_data[crop_name]

        heat_list = []
        drought_list = []
        flood_list = []
        pest_list = []

        for _, row in df.iterrows():
            heat, drought, flood, pest = analyze_risk(row, crop)
            heat_list.append(heat)
            drought_list.append(drought)
            flood_list.append(flood)
            pest_list.append(pest)

        df["Heat"] = heat_list
        df["Drought"] = drought_list
        df["Flood"] = flood_list
        df["Pest"] = pest_list

        # ---------- OUTPUT ----------
        st.subheader("📊 Detailed Forecast")
        st.dataframe(df)

        overall = get_overall(df)
        advice = get_advice(overall)

        st.subheader("⚠ Overall Risk")

        if "No major" in overall:
            st.success(overall)
        else:
            st.error(overall)

        st.subheader("🌱 Advisory")
        st.info(advice)
