import os
import random

import bleach
import requests
from amadeus import Client, ResponseError
from django.core.cache import cache
from geopy.exc import GeopyError
from geopy.geocoders import Nominatim

CSC_API_KEY = os.getenv("CSC_API_KEY")
AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")

CACHE_TIMEOUT_SECONDS = int(os.getenv("CACHE_TIMEOUT_SECONDS", "300"))

_geolocator = Nominatim(user_agent="terradart-api")

_amadeus_client = None

_ALLOWED_HTML_TAGS = [
    "b",
    "strong",
    "i",
    "em",
    "br",
    "p",
    "ul",
    "ol",
    "li",
    "a",
]

_ALLOWED_HTML_ATTRS = {
    "a": ["href", "title", "rel"],
}


def _get_cities_by_country(iso2_country_code: str):
    if not iso2_country_code or not CSC_API_KEY:
        return []

    cache_key = f"cities:{iso2_country_code.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            f"https://api.countrystatecity.in/v1/countries/{iso2_country_code}/cities",
            headers={"X-CSCAPI-KEY": CSC_API_KEY},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        cache.set(cache_key, data, timeout=CACHE_TIMEOUT_SECONDS)
        return data
    except requests.exceptions.RequestException:
        return []


def _get_countries_by_region(region: str):
    cache_key = f"countries:{region.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return {"data": cached}

    try:
        response = requests.get(
            f"https://restcountries.com/v3.1/region/{region}",
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        cache.set(cache_key, data, timeout=CACHE_TIMEOUT_SECONDS)
        return {"data": data}
    except requests.exceptions.RequestException as exception:
        return {
            "error": {"error": "Failed to fetch region data", "detail": str(exception)},
            "error_status": 502,
        }


def resolve_city_for_region(region: str, wants_capital: bool):
    countries_result = _get_countries_by_region(region)
    if "error" in countries_result:
        return countries_result
    countries = countries_result["data"]

    if not isinstance(countries, list) or not countries:
        return {
            "error": {"error": "No country data found for region", "region": region},
            "error_status": 404,
        }

    country = random.choice(countries)
    capital_list = country.get("capital") or []
    capital_city = capital_list[0] if isinstance(capital_list, list) and capital_list else None

    if wants_capital:
        return {"data": {"region": region, "city": capital_city}}

    iso2_country_code = country.get("cca2")
    cities = _get_cities_by_country(iso2_country_code)

    random_city = None
    if isinstance(cities, list) and cities:
        candidate = random.choice(cities)
        if isinstance(candidate, dict):
            random_city = candidate.get("name")

    if not random_city:
        random_city = capital_city

    return {"data": {"region": region, "city": random_city}}


def _sanitize_html(value):
    if not isinstance(value, str):
        return value

    return bleach.clean(
        value,
        tags=_ALLOWED_HTML_TAGS,
        attributes=_ALLOWED_HTML_ATTRS,
        protocols=["http", "https"],
        strip=True,
    )


def _sanitize_activity(activity):
    if not isinstance(activity, dict):
        return activity

    sanitized = dict(activity)
    for key in ("description", "shortDescription"):
        if key in sanitized:
            sanitized[key] = _sanitize_html(sanitized[key])
    return sanitized


def _sanitize_activities(data):
    if isinstance(data, list):
        return [_sanitize_activity(item) for item in data if item is not None]
    if isinstance(data, dict):
        return _sanitize_activity(data)
    return data


def _get_amadeus_client():
    global _amadeus_client
    if _amadeus_client is not None:
        return _amadeus_client

    if not AMADEUS_CLIENT_ID or not AMADEUS_CLIENT_SECRET:
        return {
            "error": {"error": "Internal Server Error"},
            "error_status": 500,
        }

    _amadeus_client = Client(
        client_id=AMADEUS_CLIENT_ID,
        client_secret=AMADEUS_CLIENT_SECRET,
    )
    return _amadeus_client


def _get_activities_by_coordinates(latitude: float, longitude: float, radius: int = 1):
    cache_key = f"activities:{latitude}:{longitude}:{radius}"
    cached = cache.get(cache_key)
    if cached is not None:
        return {"data": cached}

    client = _get_amadeus_client()
    if isinstance(client, dict) and "error" in client:
        return client

    try:
        response = client.shopping.activities.get(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
        )
        cache.set(cache_key, response.data, timeout=CACHE_TIMEOUT_SECONDS)
        return {"data": response.data}
    except ResponseError as exception:
        status_code = getattr(exception, "response", None)
        status_code = getattr(status_code, "status_code", 502)
        return {
            "error": {"error": "Failed to fetch activities", "detail": str(exception)},
            "error_status": status_code,
        }


def get_city_detail(city: str, radius: int = 1):
    base_cache_key = f"city-detail-base:{city.lower()}"
    base_data = cache.get(base_cache_key)

    if base_data is None:
        try:
            location = _geolocator.geocode(city)
        except GeopyError as exc:
            return {
                "error": {"error": "Geocoding failed", "detail": str(exc)},
                "error_status": 502,
            }

        if not location:
            return {"error": {"error": "City not found", "city": city}, "error_status": 404}

        base_data = {
            "city": city,
            "coordinates": {
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
        }
        cache.set(base_cache_key, base_data, timeout=CACHE_TIMEOUT_SECONDS)

    coordinates = base_data.get("coordinates") or {}
    latitude = coordinates.get("latitude")
    longitude = coordinates.get("longitude")
    if latitude is None or longitude is None:
        return {
            "error": {"error": "Missing coordinates for city", "city": city},
            "error_status": 500,
        }

    activities = _get_activities_by_coordinates(latitude, longitude, radius)
    if "error" in activities:
        return activities

    activities_data = activities.get("data")
    sanitized_activities = _sanitize_activities(activities_data)

    return {
        "data": {
            **base_data,
            "activities": sanitized_activities,
        }
    }

