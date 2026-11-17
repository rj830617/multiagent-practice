import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    news_api_key: str = os.getenv("NEWS_API_KEY", "")
    openweather_api_key: str = os.getenv("OPENWEATHER_API_KEY", "")
    tomtom_api_key: str = os.getenv("TOMTOM_API_KEY", "")

    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()

if not settings.groq_api_key:
    raise RuntimeError(
        "GROQ_API_KEY is not set. Copy .env.example to .env and add your Groq API key "
        "(https://console.groq.com/keys)."
    )
