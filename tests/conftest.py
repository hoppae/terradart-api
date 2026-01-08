import copy
import pytest
from unittest.mock import MagicMock, patch
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Django REST Framework API client."""
    return APIClient()


@pytest.fixture
def disable_throttling():
    """Disable throttling for tests."""
    with patch("city_detail.throttles.BaseCityThrottle.allow_request", return_value=True):
        yield


@pytest.fixture
def mock_geocoder():
    """Mock the Nominatim geocoder."""
    with patch("city_detail.services._geolocator") as mock:
        location = MagicMock()
        location.latitude = 40.7128
        location.longitude = -74.0060
        location.address = "New York, NY, USA"
        mock.geocode.return_value = location
        yield mock


@pytest.fixture
def mock_geocoder_not_found():
    """Mock geocoder returning no results."""
    with patch("city_detail.services._geolocator") as mock:
        mock.geocode.return_value = None
        yield mock


@pytest.fixture
def mock_cache():
    """Mock Django cache to always miss."""
    with patch("city_detail.services.cache") as mock:
        mock.get.return_value = None
        yield mock


@pytest.fixture
def mock_amadeus_disabled():
    """Mock Amadeus client as disabled."""
    with patch("city_detail.services._get_amadeus_client") as mock:
        mock.return_value = {"disabled": True}
        yield mock


@pytest.fixture
def mock_llm_disabled():
    """Disable LLM summary generation."""
    with patch("city_detail.services.settings") as mock:
        mock.LLM_SUMMARY_ENABLED = False
        mock.AMADEUS_ENABLED = False
        mock.FOURSQUARE_ENABLED = False
        yield mock


@pytest.fixture
def mock_env_no_api_keys(monkeypatch):
    """Remove all API keys from environment."""
    monkeypatch.delenv("CSC_API_KEY", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_ID", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("FOURSQUARE_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)


_REST_COUNTRIES_DATA = [
    {
        "name": {"common": "United States", "official": "United States of America"},
        "cca2": "US",
        "cca3": "USA",
        "capital": ["Washington, D.C."],
        "population": 331002651,
    },
    {
        "name": {"common": "Canada", "official": "Canada"},
        "cca2": "CA",
        "cca3": "CAN",
        "capital": ["Ottawa"],
        "population": 37742154,
    },
]


@pytest.fixture(scope="module")
def rest_countries_response():
    """Sample REST Countries API response."""
    return copy.deepcopy(_REST_COUNTRIES_DATA)


_STATES_DATA = [
    {"id": 1, "name": "California", "iso2": "CA", "country_code": "US"},
    {"id": 2, "name": "New York", "iso2": "NY", "country_code": "US"},
    {"id": 3, "name": "Texas", "iso2": "TX", "country_code": "US"},
]


@pytest.fixture(scope="module")
def states_response():
    """Sample states API response."""
    return copy.deepcopy(_STATES_DATA)


_CITIES_DATA = [
    {"id": 1, "name": "Los Angeles"},
    {"id": 2, "name": "San Francisco"},
    {"id": 3, "name": "San Diego"},
]


@pytest.fixture(scope="module")
def cities_response():
    """Sample cities API response."""
    return copy.deepcopy(_CITIES_DATA)


_WEATHER_DATA = {
    "current_weather": {
        "time": "2025-01-06T12:00",
        "temperature": 45.0,
        "windspeed": 10.5,
        "winddirection": 180,
        "weathercode": 0,
    },
    "hourly": {
        "time": ["2025-01-06T12:00", "2025-01-06T13:00"],
        "temperature_2m": [45.0, 46.0],
        "apparent_temperature": [42.0, 43.0],
        "relativehumidity_2m": [65, 60],
        "precipitation": [0.0, 0.0],
        "precipitation_probability": [0, 5],
        "windspeed_10m": [10.5, 11.0],
        "winddirection_10m": [180, 185],
        "cloudcover": [20, 25],
    },
    "daily": {
        "time": ["2025-01-06", "2025-01-07"],
        "temperature_2m_max": [50.0, 52.0],
        "temperature_2m_min": [35.0, 38.0],
        "precipitation_sum": [0.0, 0.1],
        "precipitation_probability_max": [10, 30],
        "weathercode": [0, 1],
    },
}


@pytest.fixture(scope="module")
def weather_response():
    """Sample OpenMeteo weather response."""
    return copy.deepcopy(_WEATHER_DATA)


_FOURSQUARE_DATA = {
    "results": [
        {
            "fsq_place_id": "abc123",
            "name": "Central Park",
            "categories": [{"name": "Park"}],
            "location": {"address": "Central Park, NY"},
            "rating": 9.5,
        },
        {
            "fsq_place_id": "def456",
            "name": "Times Square",
            "categories": [{"name": "Plaza"}],
            "location": {"address": "Times Square, NY"},
            "rating": 8.5,
        },
    ]
}


@pytest.fixture(scope="module")
def foursquare_response():
    """Sample Foursquare Places API response."""
    return copy.deepcopy(_FOURSQUARE_DATA)


_COUNTRIES_ALL_DATA = [
    {"name": {"common": "United States"}, "cca2": "US", "cca3": "USA"},
    {"name": {"common": "Canada"}, "cca2": "CA", "cca3": "CAN"},
    {"name": {"common": "Mexico"}, "cca2": "MX", "cca3": "MEX"},
]


@pytest.fixture(scope="module")
def countries_all_response():
    """Sample response for all countries endpoint."""
    return copy.deepcopy(_COUNTRIES_ALL_DATA)


@pytest.fixture
def mock_all_external_services(mock_geocoder, mock_cache, mock_llm_disabled):
    """Combined fixture for fully isolated tests with all external services mocked."""
    yield {
        "geocoder": mock_geocoder,
        "cache": mock_cache,
        "settings": mock_llm_disabled,
    }
