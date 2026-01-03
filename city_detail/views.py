from city_detail.services import (
    ALLOWED_SECTIONS,
    get_city_detail as fetch_city_detail,
    get_countries_all,
    resolve_city_for_region,
)
from city_detail.throttles import CityDetailThrottle, CityFromRegionThrottle, CountriesAllThrottle
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response


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
    wants_capital = (request.query_params.get("capital") or "false").lower() == "true"
    result = resolve_city_for_region(region, wants_capital)
    if "error" in result:
        return Response(result["error"], status=result["error_status"])
    return Response(result["data"])


@api_view(["GET"])
@throttle_classes([CityDetailThrottle])
def get_city_detail(request, city: str):
    try:
        radius = int(request.query_params.get("radius", 1))
    except ValueError:
        return Response({"error": "radius must be an integer"}, status=400)

    state = request.query_params.get("state")
    country = request.query_params.get("country")
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

