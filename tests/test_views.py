import pytest
import responses
from responses import matchers
from unittest.mock import patch, MagicMock


@pytest.mark.integration
class TestGetCountriesEndpoint:
    """Tests for /countries/ endpoint."""

    @responses.activate
    def test_returns_countries_list(self, api_client, disable_throttling, countries_all_response):
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/all",
            json=countries_all_response,
            status=200,
        )

        response = api_client.get("/countries/")
        assert response.status_code == 200
        assert len(response.json()) == 3

    @responses.activate
    def test_requests_expected_params(self, api_client, disable_throttling, countries_all_response, mock_cache):
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/all",
            match=[matchers.query_param_matcher({"fields": "name,cca2,cca3"})],
            json=countries_all_response,
            status=200,
        )

        response = api_client.get("/countries/")

        assert response.status_code == 200
        assert len(responses.calls) == 1

    @responses.activate
    def test_returns_error_on_api_failure(self, api_client, disable_throttling):
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/all",
            json={"error": "Service unavailable"},
            status=503,
        )

        with patch("city_detail.services.cache") as mock_cache:
            mock_cache.get.return_value = None
            response = api_client.get("/countries/")
        assert response.status_code == 503


@pytest.mark.integration
class TestGetStatesEndpoint:
    """Tests for /country/<country>/states/ endpoint."""

    @responses.activate
    def test_returns_states_list(self, api_client, disable_throttling, states_response):
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/states",
            json=states_response,
            status=200,
        )

        with patch("city_detail.services.CSC_API_KEY", "test-key"):
            response = api_client.get("/country/US/states/")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert data[0]["name"] == "California"


@pytest.mark.integration
class TestGetCitiesForCountryEndpoint:
    """Tests for /country/<country>/cities/ endpoint."""

    @responses.activate
    def test_returns_cities_list(self, api_client, disable_throttling, cities_response):
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/countries/US/cities",
            json=cities_response,
            status=200,
        )

        with patch("city_detail.services.CSC_API_KEY", "test-key"):
            response = api_client.get("/country/US/cities/")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert data[0]["name"] == "Los Angeles"


@pytest.mark.integration
class TestGetCitiesForStateEndpoint:
    """Tests for /country/<country>/state/<state>/cities/ endpoint."""

    @responses.activate
    def test_returns_cities_list(self, api_client, disable_throttling, cities_response):
        responses.add(
            responses.GET,
            "https://api.countrystatecity.in/v1/countries/US/states/CA/cities",
            json=cities_response,
            status=200,
        )

        with patch("city_detail.services.CSC_API_KEY", "test-key"):
            response = api_client.get("/country/US/state/CA/cities/")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert data[0]["name"] == "Los Angeles"


@pytest.mark.integration
class TestGetCityFromRegionEndpoint:
    """Tests for /get-city/region/<region>/ endpoint."""

    @responses.activate
    def test_returns_city_for_region(self, api_client, disable_throttling, rest_countries_response, states_response, cities_response):
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/region/americas",
            json=rest_countries_response,
            status=200,
        )

        response = api_client.get("/get-city/region/americas/?capital=true")
        assert response.status_code == 200
        data = response.json()
        assert "region" in data
        assert data["region"] == "americas"

    @responses.activate
    def test_returns_error_for_invalid_region(self, api_client, disable_throttling):
        responses.add(
            responses.GET,
            "https://restcountries.com/v3.1/region/nonexistent",
            json={"message": "Not Found"},
            status=404,
        )

        response = api_client.get("/get-city/region/nonexistent/")
        assert response.status_code == 502


@pytest.mark.integration
class TestGetCityDetailEndpoint:
    """Tests for /get-city-detail/<city>/ endpoint."""

    def test_returns_error_for_invalid_radius(self, api_client, disable_throttling):
        response = api_client.get("/get-city-detail/NewYork/?radius=invalid")
        assert response.status_code == 400
        assert "radius" in response.json()["error"]

    def test_returns_error_for_invalid_includes(self, api_client, disable_throttling):
        response = api_client.get("/get-city-detail/NewYork/?includes=invalid,bogus")
        assert response.status_code == 400
        assert "allowed_includes" in response.json()

    @responses.activate
    def test_returns_city_detail_with_weather(self, api_client, disable_throttling, weather_response):
        mock_location = MagicMock()
        mock_location.latitude = 40.7128
        mock_location.longitude = -74.0060

        responses.add(
            responses.GET,
            "https://api.open-meteo.com/v1/forecast",
            json=weather_response,
            status=200,
        )

        with patch("city_detail.services._geolocator") as mock_geo:
            mock_geo.geocode.return_value = mock_location
            with patch("city_detail.services.settings") as mock_settings:
                mock_settings.LLM_SUMMARY_ENABLED = False
                mock_settings.AMADEUS_ENABLED = False
                mock_settings.FOURSQUARE_ENABLED = False

                response = api_client.get("/get-city-detail/NewYork/?includes=base,weather")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "weather" in data["data"]

    @responses.activate
    def test_returns_404_for_nonexistent_city(self, api_client, disable_throttling):
        with patch("city_detail.services._geolocator") as mock_geo:
            mock_geo.geocode.return_value = None

            response = api_client.get("/get-city-detail/NonexistentCity123456/")

        assert response.status_code == 404


@pytest.mark.integration
class TestResolveIncludes:
    """Tests for _resolve_includes helper in views."""

    def test_parses_comma_separated_includes(self, api_client, disable_throttling):
        mock_location = MagicMock()
        mock_location.latitude = 40.7128
        mock_location.longitude = -74.0060

        with patch("city_detail.services._geolocator") as mock_geo:
            mock_geo.geocode.return_value = mock_location
            with patch("city_detail.services.settings") as mock_settings:
                mock_settings.LLM_SUMMARY_ENABLED = False
                mock_settings.AMADEUS_ENABLED = False
                mock_settings.FOURSQUARE_ENABLED = False

                response = api_client.get("/get-city-detail/TestCity/?includes=base")

        assert response.status_code == 200
        data = response.json()["data"]
        assert "city" in data
        assert "weather" not in data
