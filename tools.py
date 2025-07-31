from typing import Dict, Any

from langchain_core.messages import ToolMessage, AIMessage
from langchain_core.tools import tool
import requests


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


def extract_tool_calls_and_results(state_snapshots):
    tool_results = {}
    seen = set()  # для хранения (tool_call_id, result) уже выведенных

    # Собираем все результаты вызовов инструментов
    for state in reversed(state_snapshots):
        messages = state.values.get("messages", [])
        for msg in messages:
            if isinstance(msg, ToolMessage):
                tool_results[msg.tool_call_id] = msg.content

    # Проходим по истории и выводим только уникальные вызовы
    for state in reversed(state_snapshots):
        messages = state.values.get("messages", [])
        for msg in messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                printed_any = False
                for call in msg.tool_calls:
                    call_id = call["id"]
                    tool_name = call["name"]
                    args = call["args"]
                    result = tool_results.get(call_id, "<результат отсутствует>")
                    key = (call_id, str(result))
                    if key not in seen:
                        if not printed_any:
                            print(f"Step {state.metadata.get('step', '?')}:")
                            printed_any = True
                        print(f"  Tool called: {tool_name}")
                        print(f"    Args: {args}")
                        print(f"    Result: {result}")
                        seen.add(key)
                if printed_any:
                    print()
