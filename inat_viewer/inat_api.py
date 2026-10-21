# inat_api.py
import requests
from datetime import datetime
from config import INATURALIST_API_V1_TAXA

# ---- Photo helpers (used by both viewer and uploader) ----

def get_photo_url(observation, size="square"):
    photos = []
    if "observation_photos" in observation:
        for op in observation.get("observation_photos", []):
            if "photo" in op:
                photos.append(op["photo"])
    if not photos and "photos" in observation:
        photos = observation.get("photos", [])
    if photos:
        photo = photos[0]
        if size in photo:
            return photo[size]
        url = photo.get("url", "")
        if url:
            if "?size=" in url:
                url = url.split("?size=")[0]
            elif "&size=" in url:
                url = url.split("&size=")[0]
            return url
        for k in ["original", "large", "medium", "small", "square"]:
            if k in photo:
                return photo[k]
    return ""


def get_full_size_photo_url(observation):
    photos = []
    if "observation_photos" in observation:
        for op in observation.get("observation_photos", []):
            if "photo" in op:
                photos.append(op["photo"])
    if not photos and "photos" in observation:
        photos = observation.get("photos", [])
    if photos:
        url = photos[0].get("url", "")
        if url:
            return url.replace("square.jpg", "large.jpg")
    return ""


# ---- Date formatting (used by viewer) ----

def format_observed_date(time_observed_at, observed_time_zone, observed_on):
    if not time_observed_at:
        return observed_on or "N/A"
    try:
        dt = datetime.fromisoformat(time_observed_at)
        simple = dt.strftime("%Y-%m-%d %I:%M:%S %p")
        return f"{simple} ({observed_time_zone})"
    except (ValueError, TypeError):
        return observed_on or "N/A"


# ---- ID formatting (used by viewer) ----

def format_id_with_delimiters(id_value, delimiter="-", pattern="every3"):
    if not id_value:
        return id_value
    s = str(id_value)
    n = {"every2": 2, "every3": 3, "every4": 4}.get(pattern, 3)
    parts = [s[max(0, i - n):i] for i in range(len(s), 0, -n)]
    parts.reverse()
    return delimiter.join(parts)


# ---- Taxon lookup (used by viewer's taxon filter and uploader's suggestions) ----

def get_taxon_id_from_name(taxon_name):
    try:
        r = requests.get(
            INATURALIST_API_V1_TAXA,
            params={"q": taxon_name, "per_page": 1},
            timeout=5,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0]["id"] if results else None
    except Exception:
        return None
