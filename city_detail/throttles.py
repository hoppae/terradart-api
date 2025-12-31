from rest_framework.throttling import SimpleRateThrottle


class BaseCityThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        if not ident:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ident}


class CityFromRegionThrottle(BaseCityThrottle):
    scope = "city-region"


class CityDetailThrottle(BaseCityThrottle):
    scope = "city-detail"


class CityBaseThrottle(BaseCityThrottle):
    scope = "city-base"


class CityActivitiesThrottle(BaseCityThrottle):
    scope = "city-activities"


class CityPlacesThrottle(BaseCityThrottle):
    scope = "city-places"


class CityWeatherThrottle(BaseCityThrottle):
    scope = "city-weather"


class CityWikipediaThrottle(BaseCityThrottle):
    scope = "city-wikipedia"

