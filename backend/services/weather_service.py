"""
Weather and Information Service.
Queries free meteorological APIs (wttr.in / Open-Meteo) and handles offline fallbacks.
"""

import httpx
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class WeatherService:
    async def get_weather(self, city: str = "local") -> Tuple[bool, str, Dict[str, Any]]:
        target_city = city.strip() if city and city != "local" else ""
        url = f"https://wttr.in/{target_city}?format=j1" if target_city else "https://wttr.in/?format=j1"

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(url, headers={"User-Agent": "curl/7.68.0"})
                if res.status_code == 200:
                    data = res.json()
                    curr = data["current_condition"][0]
                    temp_c = curr.get("temp_C", "N/A")
                    desc = curr["weatherDesc"][0]["value"]
                    humidity = curr.get("humidity", "N/A")
                    wind = curr.get("windspeedKmph", "N/A")
                    
                    loc_name = target_city.capitalize() if target_city else "your location"
                    try:
                        area = data["nearest_area"][0]["areaName"][0]["value"]
                        loc_name = area
                    except Exception:
                        pass

                    speech = f"In {loc_name}, it is currently {temp_c}°C with {desc}. Humidity is {humidity}%."
                    return True, speech, {
                        "source": "wttr.in (External Service)",
                        "location": loc_name,
                        "temperature_c": temp_c,
                        "condition": desc,
                        "humidity": humidity,
                        "wind_speed_kmph": wind,
                    }
        except Exception as e:
            logger.warning(f"Weather API unavailable: {e}")

        # Fallback offline response
        return False, "Weather data is currently unavailable. Please verify your internet connection.", {
            "source": "Offline Fallback",
            "error": "Network unreachable"
        }


weather_service = WeatherService()
