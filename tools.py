from typing import Dict, Any
from langchain_core.tools import tool
import requests


@tool
def my_custom_tool(param1: str, param2: int) -> str:
    """Process inputs and return a string result."""
    return f"Processed {param1} and {param2}"


@tool
def add(first_int: int, second_int: int) -> int:
    """Add two integers."""
    return first_int + second_int


@tool
def exponentiate(base: int, exponent: int) -> int:
    """Exponentiate the base to the exponent power."""
    return base ** exponent


@tool
def get_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    """Get current weather for provided coordinates in Celsius."""
    try:
        response_weather = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&timezone=auto"
            f"&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m",
            timeout=10
        )
        response_weather.raise_for_status()
        return response_weather.json()["current"]
    except requests.RequestException as e:
        return {"error": str(e)}


def get_nbrb_currency_rate(currency_code):
    """Получает курс валюты по отношению к BYN."""
    try:
        url = f"https://api.nbrb.by/exrates/rates/{currency_code}?parammode=2"
        response = requests.get(url)
        response.raise_for_status()  # Проверка на ошибки HTTP

        data = response.json()
        rate = data["Cur_OfficialRate"]
        scale = data["Cur_Scale"]  # Например, для USD scale=1, а для JPY scale=100

        return rate / scale  # Возвращаем курс за 1 единицу валюты

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")
        return None
    except KeyError:
        print(f"Валюта {currency_code} не найдена или API изменилось.")
        return None

@tool
def convert_currency(from_currency: str, to_currency: str, amount: float = 1) -> float or None:
    """Convert amount from one currency to another"""
    if from_currency.upper() == "BYN":
        rate_to = get_nbrb_currency_rate(to_currency)
        if rate_to is None:
            return None
        converted_amount = amount / rate_to
    elif to_currency.upper() == "BYN":
        rate_from = get_nbrb_currency_rate(from_currency)
        if rate_from is None:
            return None
        converted_amount = amount * rate_from
    else:
        # Конвертация через BYN (например, USD → EUR)
        rate_from = get_nbrb_currency_rate(from_currency)
        rate_to = get_nbrb_currency_rate(to_currency)

        if rate_from is None or rate_to is None:
            return None

        converted_amount = (amount * rate_from) / rate_to

    return round(converted_amount, 4)


tools = [convert_currency, get_weather]
