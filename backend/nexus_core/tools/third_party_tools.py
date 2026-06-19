import urllib.request
import urllib.parse
import json
import logging
import asyncio
from typing import Dict, Any
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup

logger = logging.getLogger("nexus.tools.third_party")

async def get_weather(city: str) -> Dict[str, Any]:
    """Fetch current weather for a city using Open-Meteo (No API key required)."""
    try:
        # Step 1: Geocoding
        city_encoded = urllib.parse.quote(city)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_encoded}&count=1&language=en&format=json"
        
        req = urllib.request.Request(geo_url, headers={'User-Agent': 'Nexus-Voice-Agent'})
        with urllib.request.urlopen(req) as response:
            geo_data = json.loads(response.read().decode())
            
        if not geo_data.get("results"):
            return {"success": False, "verified": False, "result": "", "error": f"Could not find location: {city}"}
            
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
        
        res = f"The current weather in {location['name']}, {location.get('country', '')} is {temp}°C with {condition} conditions. Wind speed is {wind} km/h."
        return {"success": True, "verified": True, "result": res, "error": None}
        
    except Exception as e:
        logger.error(f"Weather tool failed: {e}")
        return {"success": False, "verified": False, "result": "", "error": f"Failed to get weather: {str(e)}"}

async def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Perform a web search using DuckDuckGo."""
    try:
        def _search():
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return results
                
        results = await asyncio.to_thread(_search)
        if not results:
            return {"success": False, "verified": False, "result": "", "error": f"No results found for '{query}'"}
            
        output = [f"Web Search Results for '{query}':"]
        for i, res in enumerate(results, 1):
            title = res.get('title', 'No Title')
            href = res.get('href', '')
            body = res.get('body', '')
            output.append(f"{i}. {title}")
            output.append(f"   URL: {href}")
            output.append(f"   Snippet: {body}")
            
        return {"success": True, "verified": True, "result": "\n".join(output), "error": None}
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return {"success": False, "verified": False, "result": "", "error": f"Error performing web search: {str(e)}"}

async def read_webpage(url: str) -> Dict[str, Any]:
    """Fetch and read the text content of a webpage."""
    try:
        def _fetch():
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                text = soup.get_text(separator=' ', strip=True)
                return text[:5000] # Return first 5000 chars to avoid overwhelming the LLM
                
        text_content = await asyncio.to_thread(_fetch)
        return {"success": True, "verified": True, "result": f"Content of {url}:\n\n{text_content}", "error": None}
    except Exception as e:
        logger.error(f"Failed to read webpage {url}: {e}")
        return {"success": False, "verified": False, "result": "", "error": f"Error reading webpage: {str(e)}"}

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
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Perform a web search using DuckDuckGo to find up-to-date information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_webpage",
            "description": "Read the text content of a specific webpage URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL of the webpage to read."
                    }
                },
                "required": ["url"]
            }
        }
    }
]
