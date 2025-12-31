from city_detail.services import (
    get_city_detail as fetch_city_detail,
    resolve_city_for_region,
)
from city_detail.throttles import (
    CityActivitiesThrottle,
    CityBaseThrottle,
    CityDetailThrottle,
    CityFromRegionThrottle,
    CityPlacesThrottle,
    CityWeatherThrottle,
    CityWikipediaThrottle,
)
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
    return Response(result)


@api_view(["GET"])
@throttle_classes([CityBaseThrottle])
def get_city_base(request, city: str):
    state = request.query_params.get("state")
    country = request.query_params.get("country")

    result = fetch_city_detail(city, 1, state, country, includes=["base"])
    if "error" in result:
        return Response(result["error"], status=result["error_status"])
    return Response(result)


@api_view(["GET"])
@throttle_classes([CityWikipediaThrottle])
def get_city_wikipedia(request, city: str):
    state = request.query_params.get("state")
    country = request.query_params.get("country")

    result = fetch_city_detail(city, 1, state, country, includes=["wikipedia"])
    if "error" in result:
        return Response(result["error"], status=result["error_status"])
    return Response(result)


@api_view(["GET"])
@throttle_classes([CityWeatherThrottle])
def get_city_weather(request, city: str):
    state = request.query_params.get("state")
    country = request.query_params.get("country")

    result = fetch_city_detail(city, 1, state, country, includes=["weather"])
    if "error" in result:
        return Response(result["error"], status=result["error_status"])
    return Response(result)


@api_view(["GET"])
@throttle_classes([CityActivitiesThrottle])
def get_city_activities(request, city: str):
    try:
        radius = int(request.query_params.get("radius", 1))
    except ValueError:
        return Response({"error": "radius must be an integer"}, status=400)

    state = request.query_params.get("state")
    country = request.query_params.get("country")

    result = fetch_city_detail(city, radius, state, country, includes=["activities"])
    if "error" in result:
        return Response(result["error"], status=result["error_status"])
    return Response(result)


@api_view(["GET"])
@throttle_classes([CityPlacesThrottle])
def get_city_places(request, city: str):
    try:
        radius = int(request.query_params.get("radius", 1))
    except ValueError:
        return Response({"error": "radius must be an integer"}, status=400)

    state = request.query_params.get("state")
    country = request.query_params.get("country")

    result = fetch_city_detail(city, radius, state, country, includes=["places"])
    if "error" in result:
        return Response(result["error"], status=result["error_status"])
    return Response(result)

