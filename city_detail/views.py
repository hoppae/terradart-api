from city_detail.services import (
    get_city_detail as fetch_city_detail,
    resolve_city_for_region,
)
from city_detail.throttles import CityDetailThrottle, CityFromRegionThrottle
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response


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

    result = fetch_city_detail(city, radius, state, country)
    if "error" in result:
        return Response(result["error"], status=result["error_status"])
    return Response(result["data"])
