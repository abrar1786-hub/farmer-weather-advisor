import streamlit as st
import requests
import pandas as pd

st.title("🌾 Farmer Climate Risk Advisor")

API_KEY = "YOUR_API_KEY"

city = st.text_input("Enter your city")
crop = st.selectbox("Select crop", ["Rice","Wheat","Maize","Cotton"])

if st.button("Check Risk"):

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

    response = requests.get(url)
    data = response.json()

    if response.status_code != 200:
        st.error("City not found")

    else:

        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]

        rainfall = 0
        if "rain" in data:
            rainfall = data["rain"].get("1h",0)

        st.subheader("Weather Data")

        st.write("Temperature:",temp,"°C")
        st.write("Humidity:",humidity,"%")
        st.write("Rainfall:",rainfall,"mm")

        st.subheader("Risk Analysis")

        if temp > 35:
            st.error("🔥 Heat Risk")

        if humidity > 80:
            st.error("🐛 Pest Risk")

        if rainfall > 80:
            st.error("🌧 Flood Risk")

        if rainfall < 5:
            st.error("🌵 Drought Risk")

        st.subheader("Advice for Farmers")

        if temp > 35:
            st.info("Irrigate crops early morning")

        if rainfall > 80:
            st.info("Ensure proper field drainage")

        if rainfall < 5:
            st.info("Use drip irrigation")

        if humidity > 80:
            st.info("Monitor pest infestation")
