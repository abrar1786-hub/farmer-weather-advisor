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
# 📍 LOCATION
# -------------------------------
def get_lat_lon(city):
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={OPENWEATHER_API_KEY}"
    res = requests.get(url).json()
    if not res:
        return None, None
    return res[0]["lat"], res[0]["lon"]

# -------------------------------
# 🌤 OPENWEATHER (FIXED)
# -------------------------------
def fetch_openweather(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    res = requests.get(url).json()

    data = []
    for i in res["list"]:
        data.append({
            "date": i["dt_txt"].split(" ")[0],
            "tmax": i["main"]["temp_max"],
            "tmin": i["main"]["temp_min"],
            "humidity": i["main"]["humidity"],
            "rain": i.get("rain", {}).get("3h", 0)
        })

    df = pd.DataFrame(data)

    # ✅ FIX: correct aggregation
    df = df.groupby("date").agg({
        "tmax": "max",
        "tmin": "min",
        "humidity": "mean",
        "rain": "sum"
    }).reset_index()

    return df

# -------------------------------
# 🌦 WEATHERAPI
# -------------------------------
def fetch_weatherapi(city):
    url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHERAPI_KEY}&q={city}&days=5"
    res = requests.get(url).json()

    data = []
    for d in res["forecast"]["forecastday"]:
        data.append({
            "date": d["date"],
            "tmax": d["day"]["maxtemp_c"],
            "tmin": d["day"]["mintemp_c"],
            "humidity": d["day"]["avghumidity"],
            "rain": d["day"]["totalprecip_mm"]
        })

    return pd.DataFrame(data)

# -------------------------------
# 🔥 SMART FUSION (IMPROVED)
# -------------------------------
def fuse_data(df1, df2):

    merged = pd.merge(df1, df2, on="date", suffixes=("_ow", "_wa"))
    final = []

    for _, row in merged.iterrows():

        # 🌡 TEMP
        if abs(row["tmax_ow"] - row["tmax_wa"]) <= 3:
            tmax = (row["tmax_ow"] + row["tmax_wa"]) / 2
        else:
            tmax = row["tmax_ow"]

        if abs(row["tmin_ow"] - row["tmin_wa"]) <= 3:
            tmin = (row["tmin_ow"] + row["tmin_wa"]) / 2
        else:
            tmin = row["tmin_ow"]

        # 🌧 RAIN
        if abs(row["rain_ow"] - row["rain_wa"]) <= 10:
            rain = (row["rain_ow"] + row["rain_wa"]) / 2
        else:
            rain = row["rain_wa"]

        # 💧 HUMIDITY
        humidity = (row["humidity_ow"] + row["humidity_wa"]) / 2

        # ✅ sanity check
        if tmax < -10 or tmax > 55:
            tmax = row["tmax_wa"]

        final.append({
            "date": row["date"],
            "tmax": round(tmax, 2),
            "tmin": round(tmin, 2),
            "rainfall": round(rain, 2),
            "humidity": round(humidity, 2)
        })

    return pd.DataFrame(final)

# -------------------------------
# ☀ NASA BASELINE
# -------------------------------
def fetch_nasa(lat, lon):
    params = {
        "parameters": "T2M_MAX,T2M_MIN,PRECTOTCORR",
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": "20000101",
        "end": "20201231",
        "format": "JSON"
    }

    res = requests.get(NASA_URL, params=params).json()
    p = res["properties"]["parameter"]

    df = pd.DataFrame({
        "tmax": list(p["T2M_MAX"].values()),
        "tmin": list(p["T2M_MIN"].values()),
        "rainfall": list(p["PRECTOTCORR"].values())
    })

    df["date"] = pd.date_range("2000-01-01", periods=len(df))
    df["month"] = df["date"].dt.month

    return df.groupby("month").mean().reset_index()

# -------------------------------
# ⚠ RISK ENGINE (FIXED)
# -------------------------------
def calculate_risk(row, crop, crop_data, base):

    c = crop_data[crop]

    # HEAT
    heat = "High" if row["tmax"] > c["tmax"] else "Low"

    # DROUGHT (FIXED)
    drought = "Low"
    if row["rainfall"] < base["rainfall"] * 0.5 and row["tmax"] > 25:
        drought = "High"

    # FLOOD
    flood = "High" if row["rainfall"] > c["max_rainfall"] else "Low"

    # PEST
    pest = "High" if row["humidity"] > c["humidity"] and 15 <= row["tmin"] <= 30 else "Low"

    return heat, drought, flood, pest

# -------------------------------
# 🌿 ADVISORY
# -------------------------------
def get_advisory(risk):
    if risk == "Heat":
        return "🔥 Increase irrigation and avoid afternoon work"
    if risk == "Drought":
        return "🌵 Use drip irrigation and conserve water"
    if risk == "Flood":
        return "🌊 Ensure proper drainage"
    if risk == "Pest":
        return "🐛 Apply pest control measures"
    return "✅ Normal farming conditions"

# -------------------------------
# 🖥 STREAMLIT UI
# -------------------------------
st.title("🌾 Climate Risk Advisor")

city = st.text_input("Enter City")
crop = st.selectbox("Select Crop", ["rice", "wheat", "maize", "cotton"])

if st.button("Check Risk"):

    with st.spinner("Fetching data... ⏳"):

        lat, lon = get_lat_lon(city)
        if not lat:
            st.error("Invalid city")
            st.stop()

        ow = fetch_openweather(lat, lon)
        wa = fetch_weatherapi(city)
        base_df = fetch_nasa(lat, lon)

        with open("crop_data.json") as f:
            crop_data = json.load(f)

        df = fuse_data(ow, wa)

        results = []
        for _, row in df.iterrows():

            month = pd.to_datetime(row["date"]).month
            base = base_df[base_df["month"] == month].iloc[0]

            heat, drought, flood, pest = calculate_risk(row, crop, crop_data, base)

            results.append({
                "Date": row["date"],
                "Tmax": row["tmax"],
                "Tmin": row["tmin"],
                "Rain": row["rainfall"],
                "Heat": heat,
                "Drought": drought,
                "Flood": flood,
                "Pest": pest
            })

        final = pd.DataFrame(results)

    # -------------------------------
    # ⚠️ SHOW RESULT FIRST
    # -------------------------------
    risks = final[["Heat","Drought","Flood","Pest"]].values.flatten()

    if "High" in risks:
        overall = "High"
    else:
        overall = "Low"

    st.subheader("⚠️ Overall Risk")

    if overall == "High":
        st.error("🚨 High Risk Detected")
    else:
        st.success("✅ No Major Risk")

    # Advisory
    if "High" in final["Drought"].values:
        advice = "🌵 Use water-saving techniques"
    elif "High" in final["Heat"].values:
        advice = "🔥 Avoid afternoon irrigation"
    elif "High" in final["Flood"].values:
        advice = "🌊 Ensure drainage"
    elif "High" in final["Pest"].values:
        advice = "🐛 Monitor pest activity"
    else:
        advice = "✅ Conditions are normal"

    st.subheader("🌿 Advisory")
    st.info(advice)

    # -------------------------------
    # 📊 TABLE AT BOTTOM
    # -------------------------------
    st.subheader("📊 Detailed Forecast")
    st.dataframe(final)
