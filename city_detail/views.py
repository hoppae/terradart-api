from city_detail.services import (
    ALLOWED_SECTIONS,
    get_cities_by_country,
    get_cities_by_state,
    get_city_detail as fetch_city_detail,
    get_countries_all,
    get_states_by_country,
    resolve_city_for_region,
)
from city_detail.throttles import (
    CitiesByCountryThrottle,
    CitiesByStateThrottle,
    CityDetailThrottle,
    CityFromRegionThrottle,
    CountriesAllThrottle,
    StatesByCountryThrottle,
)
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

MAX_INPUT_LENGTH = 100
DISALLOWED_CHARS = set("<>{}[]|\\^`")


def _validate_input(**kwargs):
    for value in kwargs.values():
        if not value:
            continue
        if len(value) > MAX_INPUT_LENGTH:
            return {"error": "Not found"}
        if any(c in DISALLOWED_CHARS for c in value):
            return {"error": "Not found"}
    return None


def _resolve_includes(params):
    includes_param = params.get("includes")
    if not includes_param:
        return None

    requested = {
        part.strip().lower()
        for part in includes_param.split(",")
        if part.strip()
    }
    return [section for section in ALLOWED_SECTIONS if section in requested]


@api_view(["GET"])
@throttle_classes([CityFromRegionThrottle])
def get_city_from_region(request, region: str):
    if error := _validate_input(region=region):
        return Response(error, status=404)
    wants_capital = (request.query_params.get("capital") or "false").lower() == "true"
    result = resolve_city_for_region(region, wants_capital)
    if "error" in result:
        return Response(result["error"], status=result["error_status"])
    return Response(result["data"])


@api_view(["GET"])
@throttle_classes([CityDetailThrottle])
def get_city_detail(request, city: str):
    state = request.query_params.get("state")
    country = request.query_params.get("country")
    if error := _validate_input(city=city, state=state, country=country):
        return Response(error, status=404)

    try:
        radius = int(request.query_params.get("radius", 1))
    except ValueError:
        return Response({"error": "radius must be an integer"}, status=400)

    includes = _resolve_includes(request.query_params)
    if includes is not None and not includes:
        return Response(
            {"error": "No valid details requested", "allowed_includes": ALLOWED_SECTIONS},
            status=400,
        )

    result = fetch_city_detail(city, radius, state, country, includes=includes)
    if "error" in result:
        return Response(result["error"], status=result["error_status"])
    return Response(result)


@api_view(["GET"])
@throttle_classes([CountriesAllThrottle])
def get_countries(request):
    result = get_countries_all()
    if "error" in result:
        return Response(result["error"], status=result["error_status"])
    return Response(result["data"])


@api_view(["GET"])
@throttle_classes([StatesByCountryThrottle])
def get_states(request, country: str):
    if error := _validate_input(country=country):
        return Response(error, status=404)
    result = get_states_by_country(country)
    if "error" in result:
        return Response(result["error"], status=result["error_status"])
    return Response(result["data"])


@api_view(["GET"])
@throttle_classes([CitiesByCountryThrottle])
def get_cities_for_country(request, country: str):
    if error := _validate_input(country=country):
        return Response(error, status=404)
    result = get_cities_by_country(country)
    if "error" in result:
        return Response(result["error"], status=result["error_status"])
    return Response(result["data"])


@api_view(["GET"])
@throttle_classes([CitiesByStateThrottle])
def get_cities_for_state(request, country: str, state: str):
    if error := _validate_input(country=country, state=state):
        return Response(error, status=404)
    result = get_cities_by_state(country, state)
    if "error" in result:
        return Response(result["error"], status=result["error_status"])
    return Response(result["data"])

