import os
import requests

def get_weather(location: str) -> str:
    """Fetch the current weather for a specified location. Provide just the city name."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key or "your_" in api_key:
         return f"OpenWeather API Key is not configured. Tell the user to set OPENWEATHER_API_KEY in their .env file to get weather for {location}."
         
    url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            desc = data['weather'][0]['description']
            temp = data['main']['temp']
            return f"The current weather in {location} is {desc} at {temp} degrees Celsius."
        return f"Could not retrieve weather data. API responded with status {response.status_code}."
    except Exception as e:
        return f"Failed to reach Weather Service: {e}"
