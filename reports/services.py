import math

from shelters.models import Refuge


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def nearest_refuges(latitude, longitude, species=None, limit=5):
    refuges = Refuge.objects.all()
    if species is not None:
        matching = refuges.filter(accepted_species=species)
        if matching.exists():
            refuges = matching

    ranked = [
        (haversine_km(latitude, longitude, refuge.latitude, refuge.longitude), refuge)
        for refuge in refuges
    ]
    ranked.sort(key=lambda item: item[0])
    return ranked[:limit]
