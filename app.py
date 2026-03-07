import streamlit as st
import requests

API_KEY = "aafce6cf9cd8393e103087fe9ca4f55a"

st.title("🌾 Farmer Weather Advisor")

city = st.text_input("Enter your city", "Coimbatore")

if st.button("Check Weather"):

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

    response = requests.get(url)
    data = response.json()

    temp = data["main"]["temp"]
    humidity = data["main"]["humidity"]

    st.subheader("Today's Weather")

    st.write("Temperature:", temp, "°C")
    st.write("Humidity:", humidity, "%")

    st.subheader("Crop Risk Status")

    if temp > 35:
        st.error("⚠ High Heat Risk for Crops")
        st.write("Advice: Increase irrigation and avoid spraying fertilizers during peak heat.")

    elif temp < 20:
        st.warning("⚠ Cold Stress Risk")
        st.write("Advice: Protect crops from cold and reduce watering.")

    elif humidity > 85:
        st.warning("⚠ Possible Fungal Disease Risk")
        st.write("Advice: Monitor crops for fungal infections.")

    else:
        st.success("✅ Weather conditions are normal for crops")
        st.write("Advice: Regular farming activities can continue.")
