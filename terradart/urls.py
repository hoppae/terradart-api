"""
URL configuration for terradart project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path

from city_detail.views import (
    get_city_base,
    get_city_activities,
    get_city_from_region,
    get_city_detail,
    get_city_places,
    get_city_weather,
    get_city_wikipedia,
)

urlpatterns = [
    path("get-city/region/<str:region>/", get_city_from_region, name="get-city-from-region"),
    path("get-city-base/<str:city>/", get_city_base, name="get-city-base"),
    path("get-city-detail/<str:city>/", get_city_detail, name="get-city-detail"),
    path("get-city-activities/<str:city>/", get_city_activities, name="get-city-activities"),
    path("get-city-places/<str:city>/", get_city_places, name="get-city-places"),
    path("get-city-weather/<str:city>/", get_city_weather, name="get-city-weather"),
    path("get-city-wikipedia/<str:city>/", get_city_wikipedia, name="get-city-wikipedia"),
]
