import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import json

# -------------------------------------------------------------
# 🔐 API KEYS (PUT YOUR KEYS HERE)
# -------------------------------------------------------------
OPENWEATHER_API_KEY = "aafce6cf9cd8393e103087fe9ca4f55a"
WEATHERAPI_KEY = "a8ac0e16da04492fa3f193535262203"

NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# -------------------------------------------------------------
# 📍 GET LAT LONG
# -------------------------------------------------------------
def get_lat_lon(city):
    try:
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={OPENWEATHER_API_KEY}"
        res = requests.get(url).json()
        if len(res) == 0:
            return None, None
        return res[0]['lat'], res[0]['lon']
    except:
        return None, None

# -------------------------------------------------------------
# 🌤️ OPENWEATHER DATA
# -------------------------------------------------------------
def fetch_openweather(lat, lon):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        data = requests.get(url).json()

        df = pd.DataFrame(data['list'])
        df['dt_txt'] = pd.to_datetime(df['dt_txt'])
        df['date'] = df['dt_txt'].dt.date

        df['tmax'] = df['main'].apply(lambda x: x['temp_max'])
        df['tmin'] = df['main'].apply(lambda x: x['temp_min'])
        df['humidity'] = df['main'].apply(lambda x: x['humidity'])
        df['rainfall'] = df['rain'].apply(lambda x: x.get('3h', 0) if isinstance(x, dict) else 0)

        daily = df.groupby('date').agg({
            'tmax': 'max',
            'tmin': 'min',
            'humidity': 'mean',
            'rainfall': 'sum'
        }).reset_index()

        return daily
    except:
        return pd.DataFrame()

# -------------------------------------------------------------
# 🌦️ WEATHER API DATA
# -------------------------------------------------------------
def fetch_weatherapi(city):
    try:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHERAPI_KEY}&q={city}&days=7"
        data = requests.get(url).json()

        rows = []
        for d in data['forecast']['forecastday']:
            rows.append({
                "date": d['date'],
                "tmax": d['day']['maxtemp_c'],
                "tmin": d['day']['mintemp_c'],
                "rainfall": d['day']['totalprecip_mm'],
                "humidity": d['day']['avghumidity']
            })

        return pd.DataFrame(rows)
    except:
        return pd.DataFrame()

# -------------------------------------------------------------
# ☀️ NASA BASELINE
# -------------------------------------------------------------
def fetch_nasa_power(lat, lon):
    try:
        params = {
            "parameters": "T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M",
            "community": "AG",
            "longitude": lon,
            "latitude": lat,
            "start": "20000101",
            "end": "20201231",
            "format": "JSON",
        }

        res = requests.get(NASA_POWER_BASE_URL, params=params).json()

        param = res['properties']['parameter']

        df = pd.DataFrame({
            "tmax": list(param['T2M_MAX'].values()),
            "tmin": list(param['T2M_MIN'].values()),
            "rainfall": list(param['PRECTOTCORR'].values()),
            "humidity": list(param['RH2M'].values())
        })

        df['date'] = pd.date_range("2000-01-01", periods=len(df))
        df['month'] = df['date'].dt.month

        return df.groupby('month').mean().reset_index()

    except:
        return pd.DataFrame()

# -------------------------------------------------------------
# 🔗 MERGE DATA
# -------------------------------------------------------------
def merge_data(df1, df2):
    if df1.empty:
        return df2
    if df2.empty:
        return df1

    df = pd.merge(df1, df2, on='date', suffixes=('_ow', '_wa'))

    df['tmax'] = df[['tmax_ow', 'tmax_wa']].mean(axis=1)
    df['tmin'] = df[['tmin_ow', 'tmin_wa']].mean(axis=1)
    df['rainfall'] = df[['rainfall_ow', 'rainfall_wa']].mean(axis=1)
    df['humidity'] = df[['humidity_ow', 'humidity_wa']].mean(axis=1)

    return df[['date', 'tmax', 'tmin', 'rainfall', 'humidity']]

# -------------------------------------------------------------
# 🌾 RISK LOGIC (FIXED DROUGHT ISSUE)
# -------------------------------------------------------------
def calculate_risks(df, crop, baseline, crop_data):
    results = []

    for _, row in df.iterrows():
        month = pd.to_datetime(row['date']).month
        base = baseline[baseline['month'] == month].iloc[0]

        crop_info = crop_data[crop]

        # Heat
        heat = "High" if row['tmax'] > crop_info['tmax'] else "Low"

        # Drought (FIXED)
        drought = "Low"
        if row['rainfall'] < base['rainfall'] * 0.7:
            drought = "High"

        # Flood
        flood = "High" if row['rainfall'] > crop_info['max_rainfall'] else "Low"

        # Pest
        pest = "High" if row['humidity'] > crop_info['humidity'] and 15 < row['tmin'] < 25 else "Low"

        results.append({
            "Date": row['date'],
            "Tmax": row['tmax'],
            "Tmin": row['tmin'],
            "Rainfall": row['rainfall'],
            "Humidity": row['humidity'],
            "Heat": heat,
            "Drought": drought,
            "Flood": flood,
            "Pest": pest
        })

    return pd.DataFrame(results)

# -------------------------------------------------------------
# 🖥️ STREAMLIT UI
# -------------------------------------------------------------
st.title("🌾 AgriGuard Climate Risk Predictor")

city = st.text_input("📍 Enter City")
crop = st.selectbox("🌱 Select Crop", ["rice", "wheat", "maize", "cotton"])

if city:
    with open("crop_data.json") as f:
        crop_data = json.load(f)

    lat, lon = get_lat_lon(city)

    if lat is None:
        st.error("❌ City not found")
    else:
        st.info("Fetching data... ⏳")

        ow = fetch_openweather(lat, lon)
        wa = fetch_weatherapi(city)
        base = fetch_nasa_power(lat, lon)

        final = merge_data(ow, wa)

        if final.empty or base.empty:
            st.error("❌ Data fetch failed")
        else:
            result = calculate_risks(final, crop, base, crop_data)
            st.success("✅ Done")
            st.dataframe(result)
