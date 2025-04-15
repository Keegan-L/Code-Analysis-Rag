import requests
from config import WEATHER_API_KEY, NEWS_API_KEY

def get_weather(city):
    url = f"https://api.weatherapi.com/v1/current.json"
    params = {"key": WEATHER_API_KEY, "q": city}
    response = requests.get(url, params=params)
    return response.json().get("current", {}).get("condition", {}).get("text", "No data")

def get_news():
    url = f"https://newsapi.org/v2/top-headlines"
    params = {"apiKey": NEWS_API_KEY, "country": "us"}
    response = requests.get(url, params=params)
    return [article["title"] for article in response.json().get("articles", [])[:3]]


