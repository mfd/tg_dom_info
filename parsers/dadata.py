"""Геокодинг через Dadata API."""

import re
from typing import Optional, Tuple

import requests

from settings import DADATA_API, DADATA_SECRET

DADATA_API_KEY = DADATA_API
DADATA_SECRET_KEY = DADATA_SECRET


def get_dadata_address(query_text: str):
    """Шаг 1: Стандартизация адреса через Dadata Clean API."""
    if not DADATA_API_KEY:
        return None, {}
    normalized_query = re.sub(r'(\d+)/(\d+)', r'\1 корпус \2', query_text)
    suggest_url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address"
    headers = {"Content-Type": "application/json", "Authorization": f"Token {DADATA_API_KEY}"}
    payload = {"query": normalized_query, "count": 1}

    try:
        response = requests.post(suggest_url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and data.get("suggestions"):
                suggestion = data["suggestions"][0]
                addr, det = suggestion.get("value"), suggestion.get("data", {})
                if DADATA_SECRET_KEY:
                    clean_url = "https://cleaner.dadata.ru/api/v1/clean/address"
                    c_headers = {"Authorization": f"Token {DADATA_API_KEY}", "X-Secret": DADATA_SECRET_KEY, "Content-Type": "application/json"}
                    c_res = requests.post(clean_url, json=[addr], headers=c_headers, timeout=5)
                    if c_res.status_code == 200:
                        c_data = c_res.json()
                        if c_data and isinstance(c_data, list):
                            det.update(c_data[0])
                return addr, det
    except Exception:
        pass
    return None, {}


def get_dadata_by_coords(lat: float, lon: float):
    """Обратный геокодинг через Dadata geolocate API. Возвращает (адрес, детали) или (None, {})."""
    if not DADATA_API_KEY:
        return None, {}
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/geolocate/address"
    headers = {"Content-Type": "application/json", "Authorization": f"Token {DADATA_API_KEY}"}
    payload = {"lat": lat, "lon": lon, "count": 1, "radius_meters": 50}
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            suggestions = res.json().get("suggestions", [])
            if suggestions:
                s = suggestions[0]
                return s.get("value"), s.get("data", {})
    except Exception:
        pass
    return None, {}
