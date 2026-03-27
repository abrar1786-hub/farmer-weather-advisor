import streamlit as st
import requests
import pandas as pd
import json

# -------------------------------
# 🔑 API KEYS
# -------------------------------
OPENWEATHER_API_KEY = "YOUR_OPENWEATHER_KEY"
WEATHERAPI_KEY = "YOUR_WEATHERAPI_KEY"

NASA_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# -------------------------------
# 📍 GET LAT/LON
# -------------------------------
def get_lat_lon(city):
    try:
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={OPENWEATHER_API_KEY}"
        res = requests.get(url).json()
        return res[0]["lat"], res[0]["lon"]
    except:
        return None, None

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

    # ✅ FIXED aggregation
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
# 🔥 SMART FUSION
# -------------------------------
def fuse_data(df1, df2):
    merged = pd.merge(df1, df2, on="date", suffixes=("_ow", "_wa"))
    final = []

    for _, row in merged.iterrows():

        # TEMP fusion
        tmax = (row["tmax_ow"] + row["tmax_wa"]) / 2 if abs(row["tmax_ow"] - row["tmax_wa"]) <= 3 else row["tmax_wa"]
        tmin = (row["tmin_ow"] + row["tmin_wa"]) / 2 if abs(row["tmin_ow"] - row["tmin_wa"]) <= 3 else row["tmin_wa"]

        # RAIN fusion
        rain = (row["rain_ow"] + row["rain_wa"]) / 2 if abs(row["rain_ow"] - row["rain_wa"]) <= 10 else row["rain_wa"]

        # HUMIDITY
        humidity = (row["humidity_ow"] + row["humidity_wa"]) / 2

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

    # HEAT (with tolerance)
    heat = "Low"
    if row["tmax"] > c["tmax"] + 2:
        heat = "High"

    # DROUGHT (corrected)
    drought = "Low"
    if row["rainfall"] < base["rainfall"] * 0.5 and row["tmax"] > 25:
        drought = "High"

    # FLOOD
    flood = "High" if row["rainfall"] > c["max_rainfall"] else "Low"

    # PEST
    pest = "High" if row["humidity"] > c["humidity"] and 15 <= row["tmin"] <= 30 else "Low"

    return heat, drought, flood, pest

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
    # 🔥 DOMINANT RISK FIX
    # -------------------------------
    risk_count = {
        "Heat": (final["Heat"] == "High").sum(),
        "Drought": (final["Drought"] == "High").sum(),
        "Flood": (final["Flood"] == "High").sum(),
        "Pest": (final["Pest"] == "High").sum(),
    }

    if all(v == 0 for v in risk_count.values()):
        main_risk = "None"
    else:
        main_risk = max(risk_count, key=risk_count.get)

    # -------------------------------
    # ⚠️ OUTPUT
    # -------------------------------
    st.subheader("⚠️ Overall Risk")

    if main_risk == "None":
        st.success("✅ No Major Risk")
    else:
        st.error(f"🚨 {main_risk} Risk Detected")

    # -------------------------------
    # 🌿 ADVISORY
    # -------------------------------
    st.subheader("🌿 Advisory")

    if main_risk == "Heat":
        st.info("🔥 Avoid afternoon work, increase irrigation")
    elif main_risk == "Drought":
        st.info("🌵 Use drip irrigation and conserve water")
    elif main_risk == "Flood":
        st.info("🌊 Ensure proper drainage")
    elif main_risk == "Pest":
        st.info("🐛 Monitor crops and apply pest control")
    else:
        st.info("✅ Normal farming conditions")

    # -------------------------------
    # 📊 TABLE LAST
    # -------------------------------
    st.subheader("📊 Detailed Forecast")
    st.dataframe(final)
