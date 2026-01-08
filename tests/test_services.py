import pytest
import responses
from unittest.mock import MagicMock, patch

from city_detail import services


class TestEligibleCountry:
    """Tests for _eligible_country helper function."""

    def test_valid_country_with_population(self):
        country = {"name": "Test", "population": 1000000}
        assert services._eligible_country(country) is True

    def test_country_with_zero_population(self):
        country = {"name": "Test", "population": 0}
        assert services._eligible_country(country) is False

    def test_country_with_negative_population(self):
        country = {"name": "Test", "population": -1}
        assert services._eligible_country(country) is False

    def test_country_without_population(self):
        country = {"name": "Test"}
        assert services._eligible_country(country) is True

    def test_non_dict_input(self):
        assert services._eligible_country("not a dict") is False
        assert services._eligible_country(None) is False
        assert services._eligible_country([]) is False


class TestPickCountry:
    """Tests for _pick_country helper function."""

    def test_picks_from_valid_countries(self):
        countries = [
            {"name": "A", "population": 100},
            {"name": "B", "population": 200},
        ]
        result = services._pick_country(countries)
        assert result in countries

    def test_empty_list_returns_none(self):
        assert services._pick_country([]) is None

    def test_none_input_returns_none(self):
        assert services._pick_country(None) is None

    def test_non_list_returns_none(self):
        assert services._pick_country("not a list") is None


class TestSanitizeHtml:
    """Tests for _sanitize_html function."""

    def test_allows_safe_tags(self):
        html = "<b>bold</b> <i>italic</i> <p>paragraph</p>"
        result = services._sanitize_html(html)
        assert "<b>bold</b>" in result
        assert "<i>italic</i>" in result

    def test_strips_unsafe_tags(self):
        html = "<script>alert('xss')</script><b>safe</b>"
        result = services._sanitize_html(html)
        assert "<script>" not in result
        assert "</script>" not in result
        assert "<b>safe</b>" in result

    def test_strips_onclick_handlers(self):
        html = '<div onclick="evil()"><b>safe</b></div>'
        result = services._sanitize_html(html)
        assert "onclick" not in result
        assert "<b>safe</b>" in result

    def test_non_string_returns_unchanged(self):
        assert services._sanitize_html(123) == 123
        assert services._sanitize_html(None) is None


class TestSanitizeActivity:
    """Tests for _sanitize_activity function."""

    def test_sanitizes_description_fields(self):
        activity = {
            "name": "Test Activity",
            "description": "<script>bad</script><b>good</b>",
            "shortDescription": "<img onerror='x'>short",
        }
        result = services._sanitize_activity(activity)
        assert "<script>" not in result["description"]
        assert "<b>good</b>" in result["description"]
        assert "onerror" not in result["shortDescription"]

    def test_non_dict_returns_unchanged(self):
        assert services._sanitize_activity("string") == "string"
        assert services._sanitize_activity(None) is None


class TestNormalizeCachePart:
    """Tests for _normalize_cache_part function."""

    def test_normalizes_string(self):
        assert services._normalize_cache_part("New York") == "new+york"
        assert services._normalize_cache_part("  PARIS  ") == "paris"

    def test_empty_string_returns_empty(self):
        assert services._normalize_cache_part("") == ""
        assert services._normalize_cache_part("   ") == ""

    def test_none_returns_empty(self):
        assert services._normalize_cache_part(None) == ""

    def test_non_string_returns_empty(self):
        assert services._normalize_cache_part(123) == ""


class TestParseIso:
    """Tests for _parse_iso function."""

    def test_parses_valid_iso_string(self):
        result = services._parse_iso("2025-01-06T12:00:00")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 6

    def test_handles_z_suffix(self):
        result = services._parse_iso("2025-01-06T12:00:00Z")
        assert result is not None

    def test_invalid_string_returns_none(self):
        assert services._parse_iso("not a date") is None

    def test_none_returns_none(self):
        assert services._parse_iso(None) is None

    def test_empty_returns_none(self):
        assert services._parse_iso("") is None


class TestNearestIndex:
    """Tests for _nearest_index function."""

    def test_finds_exact_match(self):
        series = ["2025-01-06T10:00", "2025-01-06T11:00", "2025-01-06T12:00"]
        idx = services._nearest_index("2025-01-06T11:00", series)
        assert idx == 1

    def test_finds_nearest(self):
        series = ["2025-01-06T10:00", "2025-01-06T12:00", "2025-01-06T14:00"]
        idx = services._nearest_index("2025-01-06T11:30", series)
        assert idx == 1

    def test_empty_series_returns_none(self):
        assert services._nearest_index("2025-01-06T12:00", []) is None

    def test_none_series_returns_none(self):
        assert services._nearest_index("2025-01-06T12:00", None) is None

    def test_invalid_current_returns_none(self):
        assert services._nearest_index(None, ["2025-01-06T12:00"]) is None


class TestPickIndexed:
    """Tests for _pick_indexed function."""

    def test_picks_valid_index(self):
        series = [10, 20, 30]
        assert services._pick_indexed(series, 1) == 20

    def test_none_index_returns_none(self):
        assert services._pick_indexed([1, 2, 3], None) is None

    def test_out_of_bounds_returns_none(self):
        assert services._pick_indexed([1, 2], 5) is None

    def test_non_list_returns_none(self):
        assert services._pick_indexed("not a list", 0) is None


@pytest.mark.integration
class TestGetCountriesAll:
    """Tests for get_countries_all function."""

    @responses.activate
    def test_returns_countries_on_success(self, mock_cache, countries_all_response):
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/all",
            json=countries_all_response,
            status=200,
        )

        result = services.get_countries_all()
        assert "data" in result
        assert len(result["data"]) == 3

    @responses.activate
    def test_returns_error_on_failure(self, mock_cache):
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/all",
            json={"error": "Not found"},
            status=404,
        )

        result = services.get_countries_all()
        assert "error" in result
        assert result["error_status"] == 404

    @responses.activate
    def test_caches_successful_response(self, mock_cache, countries_all_response):
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/all",
            json=countries_all_response,
            status=200,
        )

        services.get_countries_all()

        mock_cache.set.assert_called_once()
        cache_key, cached_value = mock_cache.set.call_args[0][:2]
        assert cache_key == "countries:all"
        assert cached_value == countries_all_response

    @responses.activate
    def test_uses_cache_when_available(self, mock_cache, countries_all_response):
        mock_cache.get.return_value = countries_all_response

        result = services.get_countries_all()

        assert "data" in result
        assert result["data"] == countries_all_response
        assert len(responses.calls) == 0


class TestGetStatesByCountry:
    """Tests for get_states_by_country function."""

    def test_missing_country_code_returns_error(self):
        result = services.get_states_by_country(None)
        assert "error" in result
        assert result["error_status"] == 400

    def test_empty_country_code_returns_error(self):
        result = services.get_states_by_country("")
        assert "error" in result
        assert result["error_status"] == 400


class TestGetCitiesByCountry:
    """Tests for get_cities_by_country function."""

    def test_missing_country_code_returns_error(self):
        result = services.get_cities_by_country(None)
        assert "error" in result
        assert result["error_status"] == 400


class TestGetCitiesByState:
    """Tests for get_cities_by_state function."""

    def test_missing_country_code_returns_error(self):
        result = services.get_cities_by_state(None, "CA")
        assert "error" in result
        assert result["error_status"] == 400

    def test_missing_state_code_returns_error(self):
        result = services.get_cities_by_state("US", None)
        assert "error" in result
        assert result["error_status"] == 400


class TestGeocodeCity:
    """Tests for _geocode_city function."""

    def test_successful_geocode(self, mock_geocoder):
        result = services._geocode_city("New York", "NY", "US")
        assert "location" in result
        assert result["location"].latitude == 40.7128

    def test_city_not_found(self, mock_geocoder_not_found):
        result = services._geocode_city("NonexistentCity", None, None)
        assert "error" in result
        assert result["error_status"] == 404


@pytest.mark.integration
class TestGetWeatherByCoordinates:
    """Tests for _get_weather_by_coordinates function."""

    @responses.activate
    def test_returns_weather_data(self, weather_response):
        responses.add(
            responses.GET,
            "https://api.open-meteo.com/v1/forecast",
            json=weather_response,
            status=200,
        )

        result = services._get_weather_by_coordinates(40.7128, -74.0060)
        assert "data" in result
        assert "current" in result["data"]
        assert result["data"]["current"]["temperature"] == 45.0

    @responses.activate
    def test_returns_error_on_failure(self):
        responses.add(
            responses.GET,
            "https://api.open-meteo.com/v1/forecast",
            json={"error": "Service unavailable"},
            status=503,
        )

        result = services._get_weather_by_coordinates(40.7128, -74.0060)
        assert "error" in result
        assert result["error_status"] == 503


class TestGetCitySummary:
    """Tests for _get_city_summary function."""

    def test_returns_none_when_disabled(self, mock_llm_disabled):
        result = services._get_city_summary("New York", "NY", "US")
        assert "data" in result
        assert result["data"] is None


@pytest.mark.integration
class TestGetCityDetail:
    """Tests for get_city_detail function."""

    def test_returns_error_for_invalid_city(self, mock_geocoder_not_found, mock_cache):
        result = services.get_city_detail("NonexistentCity123456")
        assert "error" in result
        assert result["error_status"] == 404

    @responses.activate
    def test_returns_base_data(self, mock_geocoder, mock_cache, mock_llm_disabled):
        result = services.get_city_detail("New York", includes=["base"])
        assert "data" in result
        assert result["data"]["city"] == "New York"
        assert "coordinates" in result["data"]

    @responses.activate
    def test_returns_weather_data(self, mock_geocoder, mock_cache, weather_response, mock_llm_disabled):
        responses.add(
            responses.GET,
            "https://api.open-meteo.com/v1/forecast",
            json=weather_response,
            status=200,
        )

        result = services.get_city_detail("New York", includes=["weather"])
        assert "data" in result
        assert "weather" in result["data"]


@pytest.mark.integration
class TestResolveCityForRegion:
    """Tests for resolve_city_for_region function."""

    @responses.activate
    def test_returns_capital_when_requested(self, mock_cache, rest_countries_response):
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/region/americas",
            json=rest_countries_response,
            status=200,
        )

        result = services.resolve_city_for_region("americas", wants_capital=True)
        assert "data" in result
        assert result["data"]["region"] == "americas"
        assert result["data"]["city"] is not None

    @responses.activate
    def test_returns_error_for_invalid_region(self, mock_cache):
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/region/invalid",
            json={"message": "Not Found"},
            status=404,
        )

        result = services.resolve_city_for_region("invalid", wants_capital=False)
        assert "error" in result


class TestGetPlacesByCoordinates:
    """Tests for _get_places_by_coordinates function."""

    def test_returns_empty_when_feature_disabled(self, mock_cache):
        with patch.object(services.settings, "FOURSQUARE_ENABLED", False):
            result = services._get_places_by_coordinates(1.0, 2.0)

        assert "data" in result
        assert result["data"] == []

    def test_errors_when_enabled_without_key(self, mock_cache):
        with patch.object(services.settings, "FOURSQUARE_ENABLED", True), patch(
            "city_detail.services.FOURSQUARE_API_KEY",
            None,
        ):
            result = services._get_places_by_coordinates(1.0, 2.0)

        assert "error" in result
        assert result["error_status"] == 500


class TestSanitizeActivities:
    """Tests for _sanitize_activities function."""

    def test_sanitizes_list_of_activities(self):
        activities = [
            {"name": "A", "description": "<script>bad</script>safe"},
            {"name": "B", "shortDescription": "<img onerror='x'>text"},
        ]
        result = services._sanitize_activities(activities)
        assert len(result) == 2
        assert "<script>" not in result[0]["description"]
        assert "onerror" not in result[1]["shortDescription"]

    def test_filters_none_values(self):
        activities = [{"name": "A"}, None, {"name": "B"}]
        result = services._sanitize_activities(activities)
        assert len(result) == 2

    def test_handles_single_dict(self):
        activity = {"description": "<script>x</script>safe"}
        result = services._sanitize_activities(activity)
        assert "<script>" not in result["description"]

    def test_returns_non_list_non_dict_unchanged(self):
        assert services._sanitize_activities("string") == "string"
        assert services._sanitize_activities(None) is None


class TestCanGeocode:
    """Tests for _can_geocode function."""

    def test_returns_true_when_location_found(self, mock_geocoder):
        result = services._can_geocode("New York", "NY", "US")
        assert result is True

    def test_returns_false_when_location_not_found(self, mock_geocoder_not_found):
        result = services._can_geocode("NonexistentCity", None, None)
        assert result is False

    def test_returns_false_for_empty_city(self):
        result = services._can_geocode("", None, None)
        assert result is False

    def test_returns_false_for_none_city(self):
        result = services._can_geocode(None, None, None)
        assert result is False

    def test_returns_false_on_geocoder_error(self):
        from geopy.exc import GeocoderTimedOut
        with patch("city_detail.services._geolocator") as mock:
            mock.geocode.side_effect = GeocoderTimedOut("timeout")
            result = services._can_geocode("TestCity", None, None)
        assert result is False


class TestGetCountryDetails:
    """Tests for _get_country_details function."""

    @responses.activate
    def test_returns_country_details(self, mock_cache):
        country_data = {
            "name": {"common": "United States", "official": "United States of America"},
            "flags": {"png": "https://example.com/flag.png"},
            "region": "Americas",
            "subregion": "North America",
        }
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/alpha/US",
            json=country_data,
            status=200,
        )

        result = services._get_country_details("US")
        assert result is not None
        assert result["name"]["common"] == "United States"

    @responses.activate
    def test_handles_list_response(self, mock_cache):
        country_data = [{"name": {"common": "Canada"}}]
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/alpha/CA",
            json=country_data,
            status=200,
        )

        result = services._get_country_details("CA")
        assert result["name"]["common"] == "Canada"

    def test_returns_none_for_empty_code(self):
        assert services._get_country_details(None) is None
        assert services._get_country_details("") is None

    @responses.activate
    def test_returns_none_on_api_error(self, mock_cache):
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/alpha/XX",
            json={"message": "Not Found"},
            status=404,
        )

        result = services._get_country_details("XX")
        assert result is None


class TestGetCitiesByCountryInternal:
    """Tests for _get_cities_by_country internal function."""

    @responses.activate
    def test_returns_cities_list(self, mock_cache):
        cities = [{"name": "Los Angeles"}, {"name": "New York"}]
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/countries/US/cities",
            json=cities,
            status=200,
        )

        with patch("city_detail.services.CSC_API_KEY", "test-key"):
            result = services._get_cities_by_country("US")

        assert len(result) == 2

    def test_returns_empty_without_api_key(self):
        with patch("city_detail.services.CSC_API_KEY", None):
            result = services._get_cities_by_country("US")
        assert result == []

    def test_returns_empty_for_empty_code(self):
        result = services._get_cities_by_country("")
        assert result == []

    @responses.activate
    def test_returns_empty_on_api_error(self, mock_cache):
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/countries/US/cities",
            json={"error": "Server error"},
            status=500,
        )

        with patch("city_detail.services.CSC_API_KEY", "test-key"):
            result = services._get_cities_by_country("US")

        assert result == []


class TestGetCitiesByStateInternal:
    """Tests for _get_cities_by_state internal function."""

    @responses.activate
    def test_returns_cities_list(self, mock_cache):
        cities = [{"name": "San Francisco"}, {"name": "Los Angeles"}]
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/countries/US/states/CA/cities",
            json=cities,
            status=200,
        )

        with patch("city_detail.services.CSC_API_KEY", "test-key"):
            result = services._get_cities_by_state("US", "CA")

        assert len(result) == 2

    def test_returns_empty_without_api_key(self):
        with patch("city_detail.services.CSC_API_KEY", None):
            result = services._get_cities_by_state("US", "CA")
        assert result == []

    def test_returns_empty_for_missing_codes(self):
        with patch("city_detail.services.CSC_API_KEY", "test-key"):
            assert services._get_cities_by_state("", "CA") == []
            assert services._get_cities_by_state("US", "") == []


class TestGetAmadeusClient:
    """Tests for _get_amadeus_client function."""

    def test_returns_disabled_when_feature_off(self):
        with patch.object(services.settings, "AMADEUS_ENABLED", False):
            result = services._get_amadeus_client()
        assert result == {"disabled": True}

    def test_returns_error_without_credentials(self):
        # Reset the cached client
        services._amadeus_client = None
        with patch.object(services.settings, "AMADEUS_ENABLED", True), \
             patch("city_detail.services.AMADEUS_CLIENT_ID", None), \
             patch("city_detail.services.AMADEUS_CLIENT_SECRET", None):
            result = services._get_amadeus_client()
        assert "error" in result
        assert result["error_status"] == 500

    def test_creates_client_with_credentials(self):
        services._amadeus_client = None
        with patch.object(services.settings, "AMADEUS_ENABLED", True), \
             patch("city_detail.services.AMADEUS_CLIENT_ID", "test-id"), \
             patch("city_detail.services.AMADEUS_CLIENT_SECRET", "test-secret"), \
             patch("city_detail.services.Client") as mock_client:
            mock_client.return_value = MagicMock()
            result = services._get_amadeus_client()
            mock_client.assert_called_once_with(
                client_id="test-id",
                client_secret="test-secret",
            )
        services._amadeus_client = None  # Reset for other tests


@pytest.mark.integration
class TestGetActivitiesByCoordinates:
    """Tests for _get_activities_by_coordinates function."""

    def test_returns_empty_when_disabled(self, mock_cache):
        with patch("city_detail.services._get_amadeus_client") as mock:
            mock.return_value = {"disabled": True}
            result = services._get_activities_by_coordinates(40.7, -74.0)
        assert result == {"data": []}

    def test_returns_error_when_client_error(self, mock_cache):
        with patch("city_detail.services._get_amadeus_client") as mock:
            mock.return_value = {"error": {"error": "No credentials"}, "error_status": 500}
            result = services._get_activities_by_coordinates(40.7, -74.0)
        assert "error" in result
        assert result["error_status"] == 500

    def test_returns_activities_on_success(self, mock_cache):
        mock_response = MagicMock()
        mock_response.data = [{"name": "Tour A"}, {"name": "Tour B"}]

        mock_client = MagicMock()
        mock_client.shopping.activities.get.return_value = mock_response

        with patch("city_detail.services._get_amadeus_client") as mock:
            mock.return_value = mock_client
            result = services._get_activities_by_coordinates(40.7, -74.0, radius=5)

        assert "data" in result
        assert len(result["data"]) == 2
        mock_client.shopping.activities.get.assert_called_once_with(
            latitude=40.7,
            longitude=-74.0,
            radius=5,
        )

    def test_returns_cached_data(self, mock_cache):
        cached_activities = [{"name": "Cached Tour"}]
        mock_cache.get.return_value = cached_activities

        result = services._get_activities_by_coordinates(40.7, -74.0)

        assert result == {"data": cached_activities}

    def test_handles_amadeus_error(self, mock_cache):
        from amadeus import ResponseError

        mock_client = MagicMock()
        mock_error = MagicMock()
        mock_error.response.status_code = 429
        mock_client.shopping.activities.get.side_effect = ResponseError(mock_error)

        with patch("city_detail.services._get_amadeus_client") as mock:
            mock.return_value = mock_client
            result = services._get_activities_by_coordinates(40.7, -74.0)

        assert "error" in result


@pytest.mark.integration
class TestGetPlacesByCoordinatesApiPath:
    """Tests for _get_places_by_coordinates API call path."""

    @responses.activate
    def test_returns_places_on_success(self, mock_cache, foursquare_response):
        responses.add(
            responses.GET,
            "https://places-api.foursquare.com/places/search",
            json=foursquare_response,
            status=200,
        )

        with patch.object(services.settings, "FOURSQUARE_ENABLED", True), \
             patch("city_detail.services.FOURSQUARE_API_KEY", "test-key"):
            result = services._get_places_by_coordinates(40.7, -74.0, radius=10)

        assert "data" in result
        assert len(result["data"]) == 2
        assert result["data"][0]["name"] == "Central Park"

    @responses.activate
    def test_handles_api_error(self, mock_cache):
        responses.add(
            responses.GET,
            "https://places-api.foursquare.com/places/search",
            json={"error": "Rate limited"},
            status=429,
        )

        with patch.object(services.settings, "FOURSQUARE_ENABLED", True), \
             patch("city_detail.services.FOURSQUARE_API_KEY", "test-key"):
            result = services._get_places_by_coordinates(40.7, -74.0)

        assert "error" in result
        assert result["error_status"] == 429

    @responses.activate
    def test_caps_radius_at_100km(self, mock_cache, foursquare_response):
        responses.add(
            responses.GET,
            "https://places-api.foursquare.com/places/search",
            json=foursquare_response,
            status=200,
        )

        with patch.object(services.settings, "FOURSQUARE_ENABLED", True), \
             patch("city_detail.services.FOURSQUARE_API_KEY", "test-key"):
            services._get_places_by_coordinates(40.7, -74.0, radius=200)

        # Check the radius param was capped at 100000 meters
        assert "radius=100000" in responses.calls[0].request.url

    def test_returns_cached_places(self, mock_cache, foursquare_response):
        mock_cache.get.return_value = foursquare_response["results"]

        with patch.object(services.settings, "FOURSQUARE_ENABLED", True):
            result = services._get_places_by_coordinates(40.7, -74.0)

        assert result == {"data": foursquare_response["results"]}


@pytest.mark.integration
class TestGetCitySummaryLlmPath:
    """Tests for _get_city_summary LLM call path."""

    def test_returns_error_without_api_key(self, mock_cache):
        with patch.object(services.settings, "LLM_SUMMARY_ENABLED", True), \
             patch("city_detail.services.LLM_API_KEY", None):
            services._llm_client = None  # Reset cached client
            result = services._get_city_summary("New York", "NY", "US")

        assert "error" in result
        assert result["error_status"] == 500

    def test_returns_summary_on_success(self, mock_cache):
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "New York is a major city."

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        with patch.object(services.settings, "LLM_SUMMARY_ENABLED", True), \
             patch("city_detail.services._get_llm_client") as mock_get_client:
            mock_get_client.return_value = mock_client
            result = services._get_city_summary("New York", "NY", "US")

        assert "data" in result
        assert result["data"] == "New York is a major city."

    def test_handles_llm_error(self, mock_cache):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with patch.object(services.settings, "LLM_SUMMARY_ENABLED", True), \
             patch("city_detail.services._get_llm_client") as mock_get_client:
            mock_get_client.return_value = mock_client
            result = services._get_city_summary("New York", "NY", "US")

        assert "error" in result

    def test_returns_cached_summary(self, mock_cache):
        mock_cache.get.return_value = "Cached summary text"

        with patch.object(services.settings, "LLM_SUMMARY_ENABLED", True):
            result = services._get_city_summary("New York", "NY", "US")

        assert result == {"data": "Cached summary text"}

    def test_includes_country_name_in_prompt(self, mock_cache):
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "Summary"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        country_details = {"name": {"common": "United States"}}

        with patch.object(services.settings, "LLM_SUMMARY_ENABLED", True), \
             patch("city_detail.services._get_llm_client") as mock_get_client, \
             patch("city_detail.services._get_country_details") as mock_country:
            mock_get_client.return_value = mock_client
            mock_country.return_value = country_details
            services._get_city_summary("Austin", "TX", "US")

        # Verify the prompt includes the full country name
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        user_message = messages[1]["content"]
        assert "United States" in user_message


@pytest.mark.slow
@pytest.mark.integration
class TestResolveCityForRegionRandomPath:
    """Tests for resolve_city_for_region random city selection path."""

    @responses.activate
    def test_returns_random_city_with_state(self, mock_cache, states_response, cities_response):
        # Use single country to avoid randomness
        single_country = [{
            "name": {"common": "United States"},
            "cca2": "US",
            "cca3": "USA",
            "capital": ["Washington, D.C."],
            "population": 331002651,
        }]
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/region/americas",
            json=single_country,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/states",
            json=states_response,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/countries/US/states/CA/cities",
            json=cities_response,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/countries/US/states/NY/cities",
            json=cities_response,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/countries/US/states/TX/cities",
            json=cities_response,
            status=200,
        )

        with patch("city_detail.services.CSC_API_KEY", "test-key"), \
             patch("city_detail.services._can_geocode") as mock_geocode:
            mock_geocode.return_value = True
            result = services.resolve_city_for_region("americas", wants_capital=False)

        assert "data" in result
        assert result["data"]["region"] == "americas"
        assert result["data"]["city"] is not None
        assert result["data"]["iso2_country_code"] == "US"

    @responses.activate
    def test_falls_back_to_capital_when_no_cities_geocode(self, mock_cache, states_response):
        # Use single country to avoid randomness
        single_country = [{
            "name": {"common": "United States"},
            "cca2": "US",
            "cca3": "USA",
            "capital": ["Washington, D.C."],
            "population": 331002651,
        }]
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/region/americas",
            json=single_country,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/states",
            json=states_response,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/countries/US/states/CA/cities",
            json=[{"name": "Test City"}],
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/countries/US/states/NY/cities",
            json=[{"name": "Test City 2"}],
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/countries/US/states/TX/cities",
            json=[{"name": "Test City 3"}],
            status=200,
        )

        with patch("city_detail.services.CSC_API_KEY", "test-key"), \
             patch("city_detail.services._can_geocode") as mock_geocode:
            mock_geocode.return_value = False  # No city can be geocoded
            result = services.resolve_city_for_region("americas", wants_capital=False)

        assert "data" in result
        # Should fall back to capital city
        assert result["data"]["city"] == "Washington, D.C."

    @responses.activate
    def test_returns_error_when_no_states(self, mock_cache, rest_countries_response):
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/region/americas",
            json=rest_countries_response,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/states",
            json=[],  # No states
            status=200,
        )

        with patch("city_detail.services.CSC_API_KEY", "test-key"):
            result = services.resolve_city_for_region("americas", wants_capital=False)

        assert "error" in result
        assert result["error_status"] == 404

    @responses.activate
    def test_returns_error_when_no_countries(self, mock_cache):
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/region/empty",
            json=[],
            status=200,
        )

        result = services.resolve_city_for_region("empty", wants_capital=False)

        assert "error" in result
        assert result["error_status"] == 404


class TestGetCityDetailAllSections:
    """Tests for get_city_detail with various section combinations."""

    @responses.activate
    def test_returns_activities_section(self, mock_geocoder, mock_cache):
        mock_activities = [{"name": "Tour A"}]

        with patch("city_detail.services._get_activities_by_coordinates") as mock_act, \
             patch.object(services.settings, "LLM_SUMMARY_ENABLED", False):
            mock_act.return_value = {"data": mock_activities}
            result = services.get_city_detail("TestCity", includes=["activities"])

        assert "data" in result
        assert "activities" in result["data"]
        assert result["data"]["activities"] == mock_activities

    @responses.activate
    def test_returns_places_section(self, mock_geocoder, mock_cache):
        mock_places = [{"name": "Central Park"}]

        with patch("city_detail.services._get_places_by_coordinates") as mock_places_fn, \
             patch.object(services.settings, "LLM_SUMMARY_ENABLED", False):
            mock_places_fn.return_value = {"data": mock_places}
            result = services.get_city_detail("TestCity", includes=["places"])

        assert "data" in result
        assert "places" in result["data"]

    @responses.activate
    def test_returns_summary_section(self, mock_geocoder, mock_cache):
        with patch("city_detail.services._get_city_summary") as mock_summary:
            mock_summary.return_value = {"data": "City summary text"}
            result = services.get_city_detail("TestCity", includes=["summary"])

        assert "data" in result
        assert result["data"]["summary"] == "City summary text"

    @responses.activate
    def test_collects_errors_from_sections(self, mock_geocoder, mock_cache):
        with patch("city_detail.services._get_weather_by_coordinates") as mock_weather, \
             patch.object(services.settings, "LLM_SUMMARY_ENABLED", False):
            mock_weather.return_value = {"error": {"error": "Weather API failed"}, "error_status": 502}
            result = services.get_city_detail("TestCity", includes=["weather"])

        assert "errors" in result
        assert "weather" in result["errors"]

    def test_returns_error_for_missing_coordinates(self, mock_geocoder, mock_cache):
        # Simulate cached base data with missing coordinates
        mock_cache.get.return_value = {"city": "Test", "coordinates": {}}

        result = services.get_city_detail("TestCity")

        assert "error" in result
        assert result["error_status"] == 500


class TestGeocodeCityFallbacks:
    """Tests for _geocode_city fallback behavior."""

    def test_tries_multiple_query_formats(self):
        call_count = 0
        def geocode_side_effect(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return None  # First two attempts fail
            mock_loc = MagicMock()
            mock_loc.latitude = 40.0
            mock_loc.longitude = -74.0
            return mock_loc

        with patch("city_detail.services._geolocator") as mock:
            mock.geocode.side_effect = geocode_side_effect
            result = services._geocode_city("TestCity", "TestState", "US")

        assert "location" in result
        assert call_count == 3

    def test_handles_timeout_gracefully(self):
        from geopy.exc import GeocoderTimedOut

        with patch("city_detail.services._geolocator") as mock:
            mock.geocode.side_effect = GeocoderTimedOut("timeout")
            result = services._geocode_city("TestCity", None, None)

        # Should continue trying other formats after timeout
        assert "error" in result
        assert result["error_status"] == 404


class TestAllowedSections:
    """Tests for ALLOWED_SECTIONS constant."""

    def test_contains_expected_sections(self):
        expected = {"base", "summary", "weather", "activities", "places"}
        assert set(services.ALLOWED_SECTIONS) == expected
