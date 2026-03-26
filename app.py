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
# 🌤 OPENWEATHER
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
    df = df.groupby("date").mean().reset_index()
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
# 🔥 SMART AGREEMENT FUSION
# -------------------------------
def fuse_data(df1, df2):

    merged = pd.merge(df1, df2, on="date", suffixes=("_ow", "_wa"))

    final = []

    for _, row in merged.iterrows():

        # 🌡 TEMP AGREEMENT
        if abs(row["tmax_ow"] - row["tmax_wa"]) <= 2:
            tmax = (row["tmax_ow"] + row["tmax_wa"]) / 2
        else:
            tmax = row["tmax_ow"]   # trust OpenWeather

        if abs(row["tmin_ow"] - row["tmin_wa"]) <= 2:
            tmin = (row["tmin_ow"] + row["tmin_wa"]) / 2
        else:
            tmin = row["tmin_ow"]

        # 🌧 RAIN AGREEMENT
        if abs(row["rain_ow"] - row["rain_wa"]) <= 10:
            rain = (row["rain_ow"] + row["rain_wa"]) / 2
        else:
            rain = row["rain_wa"]   # trust WeatherAPI

        # 💧 HUMIDITY
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
# ⚠️ RISK ENGINE
# -------------------------------
def calculate_risk(row, crop, crop_data, base):

    c = crop_data[crop]

    # HEAT
    heat = "High" if row["tmax"] > c["tmax"] else "Low"

    # DROUGHT (baseline aware)
    drought = "Low"
    if row["rainfall"] < base["rainfall"] * 0.4 and row["tmax"] > 25:
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
        return "💧 Increase irrigation and avoid afternoon work"
    if risk == "Drought":
        return "🌱 Use drip irrigation and conserve water"
    if risk == "Flood":
        return "🚜 Ensure proper drainage"
    if risk == "Pest":
        return "🐛 Monitor crops and apply pest control"

    return "✅ Normal conditions"

# -------------------------------
# 🖥 UI
# -------------------------------
st.title("🌾 Smart Climate Risk Advisor")

city = st.text_input("📍 Enter City")
crop = st.selectbox("🌱 Crop", ["rice","wheat","maize","cotton"])

if st.button("🔍 Check Risk"):

    with open("crop_data.json") as f:
        crop_data = json.load(f)

    lat, lon = get_lat_lon(city)

    if not lat:
        st.error("City not found")
    else:
        with st.spinner("Processing..."):

            ow = fetch_openweather(lat, lon)
            wa = fetch_weatherapi(city)
            base_df = fetch_nasa(lat, lon)

            df = fuse_data(ow, wa)

            results = []

            for _, row in df.iterrows():

                month = pd.to_datetime(row["date"]).month
                base = base_df[base_df["month"] == month].iloc[0]

                heat, drought, flood, pest = calculate_risk(row, crop, crop_data, base)

                results.append({
                    "date": row["date"],
                    "tmax": row["tmax"],
                    "tmin": row["tmin"],
                    "rainfall": row["rainfall"],
                    "Heat": heat,
                    "Drought": drought,
                    "Flood": flood,
                    "Pest": pest
                })

            final = pd.DataFrame(results)

            st.dataframe(final)

            # overall
            counts = {"Heat":0,"Drought":0,"Flood":0,"Pest":0}

            for _, r in final.iterrows():
                for k in counts:
                    if r[k] == "High":
                        counts[k]+=1

            if all(v==0 for v in counts.values()):
                major = "None"
            else:
                major = max(counts, key=counts.get)

            st.subheader("⚠️ Overall Risk")

            if major == "None":
                st.success("No major risk")
            else:
                st.error(f"{major} Risk Detected")

            st.subheader("🌿 Advisory")
            st.info(get_advisory(major))
