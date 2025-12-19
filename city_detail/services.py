import os
import requests

CSC_API_KEY = os.getenv("CSC_API_KEY")


def get_cities_by_country(iso2_country_code: str):
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


def get_countries_by_region(region: str):
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

