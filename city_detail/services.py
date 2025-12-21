import os
import random

import bleach
import requests
from amadeus import Client, ResponseError
from geopy.exc import GeopyError
from geopy.geocoders import Nominatim

CSC_API_KEY = os.getenv("CSC_API_KEY")
AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")

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

    try:
        response = requests.get(
            f"https://api.countrystatecity.in/v1/countries/{iso2_country_code}/cities",
            headers={"X-CSCAPI-KEY": CSC_API_KEY},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return []


def _get_countries_by_region(region: str):
    try:
        response = requests.get(
            f"https://restcountries.com/v3.1/region/{region}",
            timeout=10,
        )
        response.raise_for_status()
        return {"data": response.json()}
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
    client = _get_amadeus_client()
    if isinstance(client, dict) and "error" in client:
        return client

    try:
        response = client.shopping.activities.get(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
        )
        return {"data": response.data}
    except ResponseError as exception:
        status_code = getattr(exception, "response", None)
        status_code = getattr(status_code, "status_code", 502)
        return {
            "error": {"error": "Failed to fetch activities", "detail": str(exception)},
            "error_status": status_code,
        }


def get_city_detail(city: str, radius: int = 1):
    try:
        location = _geolocator.geocode(city)
    except GeopyError as exc:
        return {
            "error": {"error": "Geocoding failed", "detail": str(exc)},
            "error_status": 502,
        }

    if not location:
        return {"error": {"error": "City not found", "city": city}, "error_status": 404}

    activities = _get_activities_by_coordinates(location.latitude, location.longitude, radius)
    if "error" in activities:
        return activities

    activities_data = activities.get("data")
    sanitized_activities = _sanitize_activities(activities_data)

    return {
        "data": {
            "city": city,
            "coordinates": {
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            "activities": sanitized_activities,
        }
    }

