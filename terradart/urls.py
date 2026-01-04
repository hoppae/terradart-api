from django.urls import path

from city_detail.views import (
    get_cities_for_country,
    get_cities_for_state,
    get_city_detail,
    get_city_from_region,
    get_countries,
    get_states,
)

urlpatterns = [
    path("get-city/region/<str:region>/", get_city_from_region, name="get-city-from-region"),
    path("get-city-detail/<str:city>/", get_city_detail, name="get-city-detail"),
    path("countries/", get_countries, name="countries"),
    path("country/<str:country>/states/", get_states, name="states-by-country"),
    path("country/<str:country>/cities/", get_cities_for_country, name="cities-by-country"),
    path("country/<str:country>/state/<str:state>/cities/", get_cities_for_state, name="cities-by-state"),
]
