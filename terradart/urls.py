from django.urls import path

from city_detail.views import get_city_detail, get_city_from_region, get_countries

urlpatterns = [
    path("get-city/region/<str:region>/", get_city_from_region, name="get-city-from-region"),
    path("get-city-detail/<str:city>/", get_city_detail, name="get-city-detail"),
    path("countries/", get_countries, name="countries"),
]
