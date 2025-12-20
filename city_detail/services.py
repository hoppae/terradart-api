import os
import random

import requests

CSC_API_KEY = os.getenv("CSC_API_KEY")


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

