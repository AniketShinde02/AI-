import urllib.request
import urllib.parse
import json
import logging

logger = logging.getLogger("nexus.tools.third_party")

async def get_weather(city: str) -> str:
    """Fetch current weather for a city using Open-Meteo (No API key required)."""
    try:
        # Step 1: Geocoding
        city_encoded = urllib.parse.quote(city)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_encoded}&count=1&language=en&format=json"
        
        req = urllib.request.Request(geo_url, headers={'User-Agent': 'Nexus-Voice-Agent'})
        with urllib.request.urlopen(req) as response:
            geo_data = json.loads(response.read().decode())
            
        if not geo_data.get("results"):
            return f"Could not find location: {city}"
            
        location = geo_data["results"][0]
        lat, lon = location["latitude"], location["longitude"]
        
        # Step 2: Weather Data
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,is_day,precipitation,weather_code,wind_speed_10m&timezone=auto"
        req = urllib.request.Request(weather_url, headers={'User-Agent': 'Nexus-Voice-Agent'})
        
        with urllib.request.urlopen(req) as response:
            weather_data = json.loads(response.read().decode())
            
        current = weather_data.get("current", {})
        code = current.get("weather_code", 0)
        
        condition = 'Clear'
        if code in [1, 2, 3]: condition = 'Cloudy'
        elif code in [45, 48]: condition = 'Haze'
        elif 51 <= code <= 67: condition = 'Rain'
        elif 71 <= code <= 77: condition = 'Snow'
        elif 95 <= code <= 99: condition = 'Thunderstorm'
        
        temp = current.get("temperature_2m")
        wind = current.get("wind_speed_10m")
        
        return f"The current weather in {location['name']}, {location.get('country', '')} is {temp}°C with {condition} conditions. Wind speed is {wind} km/h."
        
    except Exception as e:
        logger.error(f"Weather tool failed: {e}")
        return f"Failed to get weather: {str(e)}"

THIRD_PARTY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather conditions for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The name of the city, e.g. 'London', 'Mumbai', 'New York'"
                    }
                },
                "required": ["city"]
            }
        }
    }
]
