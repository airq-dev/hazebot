import math


def get_pm25_display(pm25: float) -> str:
    if pm25 <= 12:
        return "Good"
    elif pm25 <= 35:
        return "Moderate"
    elif pm25 <= 55:
        return "Unhealthy for Sensitive Individuals"
    elif pm25 <= 150:
        return "Unhealthy"
    elif pm25 <= 250:
        return "Very Unhealthy"
    else:
        return "Hazardous"


def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers. Use 3956 for miles
    return c * r
