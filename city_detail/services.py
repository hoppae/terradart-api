import os
import random
import re
from datetime import datetime

import bleach
import requests
from amadeus import Client, ResponseError
from django.core.cache import cache
from geopy.exc import GeocoderTimedOut, GeopyError
from geopy.geocoders import Nominatim
from urllib.parse import quote_plus

CSC_API_KEY = os.getenv("CSC_API_KEY")
AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")

CACHE_TIMEOUT_SECONDS = int(os.getenv("CACHE_TIMEOUT_SECONDS", "300"))

_geolocator = Nominatim(user_agent="terradart-api", timeout=5)

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


def _eligible_country(country):
    if not isinstance(country, dict):
        return False
    population = country.get("population")
    if isinstance(population, (int, float)) and population <= 0:
        return False
    return True


def _pick_country(countries):
    if not isinstance(countries, list) or not countries:
        return None
    for _ in range(len(countries)):
        candidate = random.choice(countries)
        if _eligible_country(candidate):
            return candidate
    return random.choice(countries)


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
            timeout=5,
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
            params={"fields": "capital,name,cca2,cca3,population"},
            timeout=5,
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


def _get_country_details(iso2_country_code: str | None):
    if not iso2_country_code:
        return None

    cache_key = f"country-info:{iso2_country_code.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            f"https://restcountries.com/v3.1/alpha/{iso2_country_code}",
            params={"fields": "name,flags,region,subregion"},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data:
            data = data[0]
        cache.set(cache_key, data, timeout=CACHE_TIMEOUT_SECONDS)
        return data
    except requests.exceptions.RequestException:
        return None


def _get_states_by_country(iso2_country_code: str):
    if not iso2_country_code or not CSC_API_KEY:
        return []

    cache_key = f"states:{iso2_country_code.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            f"https://api.countrystatecity.in/v1/countries/{iso2_country_code}/states",
            headers={"X-CSCAPI-KEY": CSC_API_KEY},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        cache.set(cache_key, data, timeout=CACHE_TIMEOUT_SECONDS)
        return data
    except requests.exceptions.RequestException:
        return []


def _get_cities_by_state(iso2_country_code: str, iso2_state_code: str):
    if not iso2_country_code or not iso2_state_code or not CSC_API_KEY:
        return []

    cache_key = f"state-cities:{iso2_country_code.lower()}:{iso2_state_code.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            f"https://api.countrystatecity.in/v1/countries/{iso2_country_code}/states/{iso2_state_code}/cities",
            headers={"X-CSCAPI-KEY": CSC_API_KEY},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        cache.set(cache_key, data, timeout=CACHE_TIMEOUT_SECONDS)
        return data
    except requests.exceptions.RequestException:
        return []


def resolve_city_for_region(region: str, wants_capital: bool):
    countries_result = _get_countries_by_region(region)
    if "error" in countries_result:
        return countries_result
    countries = countries_result["data"]

    country = _pick_country(countries)

    if country is None:
        return {
            "error": {"error": "No country data found for region", "region": region},
            "error_status": 404,
        }

    iso2_country_code = country.get("cca2")
    iso3_country_code = country.get("cca3")
    capital_list = country.get("capital") or []
    capital_city = capital_list[0] if isinstance(capital_list, list) and capital_list else None

    if wants_capital:
        return {
            "data": {
                "region": region,
                "city": capital_city,
                "iso2_country_code": iso2_country_code,
                "iso3_country_code": iso3_country_code,
            }
        }

    states = _get_states_by_country(iso2_country_code)
    if not isinstance(states, list) or not states:
        return {
            "error": {"error": "No states found for country", "country": iso2_country_code},
            "error_status": 404,
        }

    random_city = None
    state_iso2 = None
    state_name = None

    # Try a few random states to find one with cities that can be geocoded
    for _ in range(min(len(states), 5)):
        state_choice = random.choice(states)
        state_iso2_candidate = state_choice.get("iso2")
        state_name_candidate = state_choice.get("name")
        if not state_iso2_candidate:
            continue

        cities = _get_cities_by_state(iso2_country_code, state_iso2_candidate)
        if isinstance(cities, list) and cities:
            candidate = random.choice(cities)
            if isinstance(candidate, dict):
                city_name = candidate.get("name")
                if _can_geocode(city_name, state_name_candidate, iso2_country_code):
                    random_city = city_name
                    state_iso2 = state_iso2_candidate
                    state_name = state_name_candidate
                    break

    if not random_city:
        random_city = capital_city

    if not random_city:
        return {
            "error": {"error": "No city found for region", "region": region, "country": iso2_country_code},
            "error_status": 404,
        }

    return {
        "data": {
            "region": region,
            "city": random_city,
            "iso2_country_code": iso2_country_code,
            "iso3_country_code": iso3_country_code,
            "state_name": state_name,
            "iso2_state_code": state_iso2,
        }
    }


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


def _normalize_cache_part(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().lower()
    if not normalized:
        return ""
    return quote_plus(normalized)


def _can_geocode(city: str | None, state: str | None, country_iso2: str | None) -> bool:
    if not city:
        return False
    parts = [city]
    if state:
        parts.append(state)
    if country_iso2:
        parts.append(country_iso2)
    query = ", ".join(parts)
    try:
        location = _geolocator.geocode(query, country_codes=country_iso2)
        return location is not None
    except GeopyError:
        return False


def _geocode_city(city: str, state: str | None, country: str | None):
    attempts = []
    parts = [city]

    if state:
        parts.append(state)
    if country:
        parts.append(country)

    attempts.append((", ".join(parts), country))

    if country and state:
        attempts.append((f"{city}, {country}", country))

    attempts.append((city, None))

    for query, country_code in attempts:
        try:
            location = _geolocator.geocode(query, country_codes=country_code, timeout=5)
        except GeocoderTimedOut:
            location = None
        except GeopyError as exc:
            return {
                "error": {"error": "Geocoding failed", "detail": str(exc)},
                "error_status": 502,
            }
        if location:
            return {"location": location}

    return {
        "error": {"error": "City not found", "city": city, "state": state, "country": country},
        "error_status": 404,
    }


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


def _parse_iso(ts: str | None):
    if not ts or not isinstance(ts, str):
        return None
    try:
        ts_norm = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts_norm)
    except Exception:
        return None


def _nearest_index(current_ts: str | None, series: list[str] | None):
    cur_dt = _parse_iso(current_ts)
    if not cur_dt or not isinstance(series, list) or not series:
        return None
    best_idx = None
    best_delta = None
    for i, ts in enumerate(series):
        dt = _parse_iso(ts)
        if not dt:
            continue
        delta = abs((dt - cur_dt).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_idx = i
    return best_idx


def _pick_indexed(series, idx):
    if idx is not None and isinstance(series, list) and len(series) > idx:
        return series[idx]
    return None


def _get_weather_by_coordinates(latitude: float, longitude: float):
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current_weather": True,
                "hourly": ",".join(
                    [
                        "temperature_2m",
                        "apparent_temperature",
                        "relativehumidity_2m",
                        "precipitation",
                        "precipitation_probability",
                        "windspeed_10m",
                        "winddirection_10m",
                        "cloudcover",
                    ]
                ),
                "daily": ",".join(
                    [
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "precipitation_sum",
                        "precipitation_probability_max",
                        "weathercode",
                    ]
                ),
                "forecast_days": 2,
                "timezone": "auto",
                "temperature_unit": "fahrenheit",
                "windspeed_unit": "mph",
            },
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()

        current = data.get("current_weather") or {}
        hourly = data.get("hourly") or {}
        hourly_time = hourly.get("time") or []

        # Align current time with nearest hourly metrics to get humidity/precip/clouds
        current_time = current.get("time")
        idx = _nearest_index(current_time, hourly_time)

        current_payload = {
            "time": current_time,
            "temperature": current.get("temperature"),
            "apparent_temperature": _pick_indexed(hourly.get("apparent_temperature", []), idx),
            "humidity": _pick_indexed(hourly.get("relativehumidity_2m", []), idx),
            "precipitation": _pick_indexed(hourly.get("precipitation", []), idx),
            "precipitation_probability": _pick_indexed(hourly.get("precipitation_probability", []), idx),
            "windspeed": current.get("windspeed"),
            "winddirection": current.get("winddirection"),
            "cloudcover": _pick_indexed(hourly.get("cloudcover", []), idx),
            "weathercode": current.get("weathercode"),
        }

        daily = data.get("daily") or {}
        next_day = None

        if isinstance(daily.get("time"), list) and len(daily.get("time")) > 1:
            next_day = {
                "date": daily["time"][1],
                "temperature_max": daily.get("temperature_2m_max", [None, None])[1],
                "temperature_min": daily.get("temperature_2m_min", [None, None])[1],
                "precipitation_sum": daily.get("precipitation_sum", [None, None])[1],
                "precipitation_probability_max": daily.get("precipitation_probability_max", [None, None])[1],
                "weathercode": daily.get("weathercode", [None, None])[1],
            }

        return {"data": {"current": current_payload, "next_day": next_day, "raw": data}}
    except requests.exceptions.RequestException as exception:
        status_code = getattr(getattr(exception, "response", None), "status_code", 502)
        return {
            "error": {"error": "Failed to fetch weather", "detail": str(exception)},
            "error_status": status_code,
        }


def _fetch_extract(title: str):
    response = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "prop": "extracts",
            "exintro": "",
            "explaintext": "",
            "format": "json",
            "titles": title,
        },
        headers={
            "User-Agent": "terradart-api (contact: admin@terradart.com)",
        },
        timeout=5,
    )
    response.raise_for_status()
    data = response.json()
    pages = data.get("query", {}).get("pages", {})
    if isinstance(pages, dict) and pages:
        first_page = next(iter(pages.values()))
        extract = first_page.get("extract")
        return _clean_first_sentence(extract)
    return None


def _extract_mentions_location(extract: str | None, state_name: str | None, country_name: str | None):
    if not extract:
        return False
    text = extract.lower()
    if state_name and state_name.lower() in text:
        return True
    if country_name and country_name.lower() in text:
        return True
    return False


def _clean_first_sentence(extract: str | None) -> str | None:
    if not isinstance(extract, str):
        return extract

    parts = re.split(r"(?<=[.!?])\s", extract, maxsplit=1)
    first = parts[0] if parts else extract
    rest = parts[1] if len(parts) > 1 else ""

    # manual cleanup for missing text
    first = first.replace("()", "").replace("(, ", "(").replace("(;", "(").replace("( ", "(").replace("( ", "(").replace("(; ", "(")

    if rest:
        return f"{first} {rest}"
    return first


def _wiki_opensearch(term: str, limit: int = 5):
    response = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "opensearch",
            "search": term,
            "limit": limit,
            "namespace": 0,
            "format": "json",
            "redirects": "resolve"
        },
        headers={
            "User-Agent": "terradart-api (contact: admin@terradart.com)",
        },
        timeout=5,
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
        return data[1]
    return []


def _get_wikipedia_extract(city: str, state: str | None = None, country: str | None = None):
    country_name = None

    if country:
        country_details = _get_country_details(country)
        if isinstance(country_details, dict):
            name_info = country_details.get("name") or {}
            country_name = name_info.get("common") or name_info.get("official")
        if not country_name:
            country_name = country

    try:
        chosen_extract = None

        if state:
            title = f"{city}, {state}"
            extract = _fetch_extract(title)

            if extract:
                chosen_extract = extract
            else:
                if country_name:
                    country_title = f"{city}, {country_name}"
                    country_extract = _fetch_extract(country_title)
                    if country_extract:
                        chosen_extract = country_extract

                if chosen_extract is None:
                    extract = _fetch_extract(city)
                    has_location = _extract_mentions_location(extract, state, country_name)
                    if has_location:
                        chosen_extract = extract

        else:
            extract = _fetch_extract(city)
            has_location = _extract_mentions_location(extract, None, country_name)

            if has_location:
                chosen_extract = extract
            elif country_name:
                country_title = f"{city}, {country_name}"
                country_extract = _fetch_extract(country_title)
                if country_extract:
                    chosen_extract = country_extract

        if chosen_extract is None:
            titles = _wiki_opensearch(city, limit=5)
            if isinstance(titles, list) and titles:
                for opensearch_title in titles:
                    extract = _fetch_extract(opensearch_title)
                    if _extract_mentions_location(extract, state, country_name):
                        chosen_extract = extract
                        break

        return {"data": chosen_extract}
    except requests.exceptions.RequestException as exception:
        return {
            "error": {"error": "Failed to fetch Wikipedia extract", "detail": str(exception)},
            "error_status": 502,
        }


def get_city_detail(city: str, radius: int = 1, state: str | None = None, country: str | None = None):
    cache_city = _normalize_cache_part(city)
    cache_state = _normalize_cache_part(state)
    cache_country = _normalize_cache_part(country)


    base_cache_key = f"city-detail-base:{cache_city}:{cache_state}:{cache_country}"
    base_data = cache.get(base_cache_key)

    if base_data is None:
        geocode_result = _geocode_city(city, state, country)
        if "error" in geocode_result:
            return geocode_result
        location = geocode_result["location"]

        country_details = _get_country_details(country)

        base_data = {
            "city": city,
            "coordinates": {
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            "state": state,
            "country": country,
            "country_details": country_details,
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

    weather = _get_weather_by_coordinates(latitude, longitude)
    if "error" in weather:
        return weather

    wiki_extract = _get_wikipedia_extract(city, state, country)
    wiki_extract_text = None if "error" in wiki_extract else wiki_extract.get("data")

    activities_data = activities.get("data")
    sanitized_activities = _sanitize_activities(activities_data)
    weather_data = weather.get("data")

    return {
        "data": {
            **base_data,
            "activities": sanitized_activities,
            "weather": weather_data,
            "wikipedia_extract": wiki_extract_text,
        }
    }

