# uploader/helpers.py
import time
import threading
import requests
from datetime import datetime
from config import (
    INATURALIST_API_V2_BASE, MIN_WRITE_GAP_SECONDS,
)

# Global throttle state (shared across all requests in this process)
_UPLOAD_LOCK = threading.Lock()
_LAST_WRITE_TS = 0.0


def wait_for_rate_limit():
    """Block until at least MIN_WRITE_GAP_SECONDS since the last write."""
    global _LAST_WRITE_TS
    wait = MIN_WRITE_GAP_SECONDS - (time.time() - _LAST_WRITE_TS)
    if wait > 0:
        time.sleep(wait)


def mark_write_done():
    global _LAST_WRITE_TS
    _LAST_WRITE_TS = time.time()


def upload_one_photo(token, obs_uuid, file):
    """
    Upload a single photo to an observation, respecting rate limits.
    Returns the parsed JSON response or raises.
    """
    with _UPLOAD_LOCK:
        wait_for_rate_limit()
        resp = requests.post(
            f"{INATURALIST_API_V2_BASE}/observation_photos",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (file.filename, file.stream, file.mimetype)},
            data={"observation_id": obs_uuid},
            timeout=(10, 120),
        )
        mark_write_done()
    resp.raise_for_status()
    return resp.json()


def reorder_photos(token, photo_positions):
    """photo_positions: [{id, position}, ...]"""
    results = []
    for item in photo_positions:
        with _UPLOAD_LOCK:
            wait_for_rate_limit()
            resp = requests.put(
                f"{INATURALIST_API_V2_BASE}/observation_photos/{item['id']}",
                headers={"Authorization": f"Bearer {token}"},
                json={"observation_photo": {"position": item["position"]}},
                timeout=(10, 30),
            )
            mark_write_done()
        results.append({"id": item["id"], "status": resp.status_code})
        if resp.status_code == 429:
            break
    return results


def haversine_km(lat1, lon1, lat2, lon2):
    import math
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = (math.sin(dlat / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def parse_obs_time(obs):
    """Return (datetime, has_precise_time). Falls back to noon of observed_on."""
    t = obs.get("time_observed_at")
    if t:
        try:
            return datetime.fromisoformat(t.replace("Z", "+00:00")).replace(tzinfo=None), True
        except ValueError:
            pass
    d = obs.get("observed_on")
    if d:
        try:
            return datetime.fromisoformat(d + "T12:00:00"), False
        except ValueError:
            pass
    return None, False


def score_group_against_observation(group, obs):
    """Return (score, gap_minutes, precise, distance_km) or None if too weak."""
    import math
    g_start = datetime.fromisoformat(group["start"])
    g_end = datetime.fromisoformat(group["end"])
    g_gps = group.get("gps")

    obs_time, precise = parse_obs_time(obs)
    if obs_time is None:
        return None

    if g_start <= obs_time <= g_end:
        gap_min = 0.0
        time_score = 100.0
    else:
        if obs_time < g_start:
            gap_min = (g_start - obs_time).total_seconds() / 60
        else:
            gap_min = (obs_time - g_end).total_seconds() / 60
        time_score = 100.0 * math.exp(-gap_min / 60)

    if not precise:
        time_score *= 0.5

    loc_score = 1.0
    distance_km = None
    if g_gps and obs.get("location"):
        try:
            lat, lon = map(float, obs["location"].split(","))
            distance_km = haversine_km(g_gps["lat"], g_gps["lon"], lat, lon)
            if distance_km > 0.1:
                loc_score = max(0.1, 1.0 - distance_km / 10.0)
        except (ValueError, TypeError):
            pass

    final = time_score * loc_score
    if final < 5:
        return None
    return final, gap_min, precise, distance_km
