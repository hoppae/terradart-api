import random

from city_detail.services import get_cities_by_country, get_countries_by_region
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def get_city_from_region(request, region: str):
    wants_capital = (request.query_params.get("capital") or "false").lower() == "true"

    data = get_countries_by_region(region)
    if "error" in data:
        return Response(data["error"], status=data["error_status"])
    data = data["data"]

    if not isinstance(data, list) or not data:
        return Response(
            {"error": "No country data found for region", "region": region},
            status=404,
        )

    random_entry = random.choice(data)

    capital_list = random_entry.get("capital") or []
    capital_city = capital_list[0] if isinstance(capital_list, list) and capital_list else None

    if wants_capital:
        return Response({"region": region, "city": capital_city})

    iso2_country_code = random_entry.get("cca2")
    cities = get_cities_by_country(iso2_country_code)

    random_city = None
    if isinstance(cities, list) and cities:
        candidate = random.choice(cities)
        if isinstance(candidate, dict):
            random_city = candidate.get("name")

    if not random_city:
        random_city = capital_city

    return Response({"region": region, "city": random_city})
