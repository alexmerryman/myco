# inat_auth.py
from flask import Blueprint, redirect, request, session, url_for
import requests
from config import (
    INATURALIST_TOKEN_URL, INAT_CLIENT_ID, INAT_CLIENT_SECRET,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/inat/login")
def inat_login():
    return redirect(
        "https://www.inaturalist.org/oauth/authorize"
        f"?client_id={INAT_CLIENT_ID}&response_type=code"
        f"&redirect_uri={url_for('auth.inat_callback', _external=True)}"
    )


@auth_bp.route("/inat/callback")
def inat_callback():
    code = request.args.get("code")
    if not code:
        return "Missing authorization code", 400

    # IMPORTANT: The redirect_uri must be EXACTLY the same as the one
    # you sent in the initial /inat/login redirect.
    redirect_uri = url_for("auth.inat_callback", _external=True)

    r = requests.post(
        INATURALIST_TOKEN_URL,
        data={
            "client_id": INAT_CLIENT_ID,
            "client_secret": INAT_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,  # <-- This is often the missing param
        },
        timeout=30,
    )
    r.raise_for_status()
    session["inat_token"] = r.json()["access_token"]
    return redirect(url_for("uploader.index"))
