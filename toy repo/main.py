from api import get_weather, get_news
from utils import log_data

def main():
    city = "New York"
    weather = get_weather(city)
    news = get_news()

    log_data("weather", weather)
    log_data("news", news)

    print(f"Weather in {city}: {weather}")
    print(f"Today's news: {news}")

if __name__ == "__main__":
    main()

