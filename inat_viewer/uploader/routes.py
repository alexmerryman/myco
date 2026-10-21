# uploader/routes.py
from flask import (
    Blueprint, render_template, request, jsonify, session,
    redirect, url_for, current_app,
)
import requests
from datetime import datetime, timedelta

from config import (
    INATURALIST_API_V2, INATURALIST_API_V2_BASE,
)
from .helpers import (
    upload_one_photo, reorder_photos, score_group_against_observation,
)

uploader_bp = Blueprint(
    "uploader",
    __name__,
    template_folder="templates",   # uploader/templates/uploader.html
)


def _require_token():
    if "inat_token" not in session:
        return redirect(url_for("auth.inat_login"))
    return None


@uploader_bp.route("/uploader")
def index():
    guard = _require_token()
    if guard:
        return guard
    return render_template("uploader.html")


# ---------- Observation lookup ----------

@uploader_bp.route("/api/observation-id/<int:obs_id>")
def get_observation_by_id(obs_id):
    token = session.get("inat_token")
    r = requests.get(
        f"{INATURALIST_API_V2}/{obs_id}",
        params={"fields": "id,uuid"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if r.status_code == 404:
        return jsonify({"error": "not found"}), 404
    r.raise_for_status()
    data = r.json()["results"][0]
    return jsonify({"id": data["id"], "uuid": data["uuid"]})


@uploader_bp.route("/api/observation/<int:obs_id>/photos")
def get_observation_photos(obs_id):
    token = session.get("inat_token")
    r = requests.get(
        f"{INATURALIST_API_V2}/{obs_id}",
        params={
            "fields": (
                "id,uuid,"
                "observation_photos.id,"
                "observation_photos.position,"
                "observation_photos.photo.url,"
                "observation_photos.photo.original"
            ),
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()["results"][0]
    photos = sorted(
        data.get("observation_photos", []),
        key=lambda p: p.get("position", 0),
    )
    return jsonify({"uuid": data["uuid"], "photos": photos})


# ---------- Suggestions ----------

@uploader_bp.route("/api/suggest-observations", methods=["POST"])
def suggest_observations():
    token = session.get("inat_token")
    groups = (request.get_json() or {}).get("groups", [])
    if not groups:
        return jsonify({"results": []})

    starts = [datetime.fromisoformat(g["start"]) for g in groups]
    ends = [datetime.fromisoformat(g["end"]) for g in groups]
    win_start = min(starts) - timedelta(days=1)
    win_end = max(ends) + timedelta(days=1)

    observations = []
    page = 1
    while True:
        r = requests.get(
            INATURALIST_API_V2,
            params={
                "user_id": "me",
                "d1": win_start.strftime("%Y-%m-%d"),
                "d2": win_end.strftime("%Y-%m-%d"),
                "fields": (
                    "id,uuid,observed_on,time_observed_at,observed_time_zone,"
                    "taxon.name,taxon.preferred_common_name,"
                    "location,place_guess,"
                    "observation_photos.id,"
                    "observation_photos.photo.square"
                ),
                "per_page": 200,
                "page": page,
                "order_by": "observed_on",
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        observations.extend(data.get("results", []))
        if not data.get("results") or len(observations) >= data.get("total_results", 0):
            break
        page += 1

    results = []
    for idx, group in enumerate(groups):
        candidates = []
        for obs in observations:
            scored = score_group_against_observation(group, obs)
            if scored is None:
                continue
            score, gap_min, precise, distance_km = scored
            candidates.append({
                "observation": obs,
                "score": round(score, 1),
                "time_gap_minutes": round(gap_min, 1),
                "time_precise": precise,
                "distance_km": round(distance_km, 2) if distance_km is not None else None,
            })
        candidates.sort(key=lambda c: c["score"], reverse=True)
        results.append({"group_index": idx, "suggestions": candidates[:5]})

    return jsonify({"results": results})


# ---------- Upload & reorder ----------

@uploader_bp.route("/api/upload-photo", methods=["POST"])
def upload_photo():
    token = session.get("inat_token")
    obs_uuid = request.form["observation_uuid"]
    file = request.files["photo"]

    try:
        data = upload_one_photo(token, obs_uuid, file)
        return jsonify(data)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            retry_after = int(e.response.headers.get("Retry-After", "5"))
            return jsonify({"error": "rate_limited", "retry_after": retry_after}), 429
        raise


@uploader_bp.route("/api/reorder-photos", methods=["POST"])
def reorder():
    token = session.get("inat_token")
    payload = request.get_json() or {}
    results = reorder_photos(token, payload.get("photos", []))
    return jsonify({"results": results})
