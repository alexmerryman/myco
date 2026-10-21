# config.py
import os
from dotenv import load_dotenv

load_dotenv()   # this module is the first thing that touches env vars

INATURALIST_API_V2 = "https://api.inaturalist.org/v2/observations"
INATURALIST_API_V2_BASE = "https://api.inaturalist.org/v2"
INATURALIST_API_V1_TAXA = "https://api.inaturalist.org/v1/taxa"
INATURALIST_TOKEN_URL = "https://www.inaturalist.org/oauth/token"

PER_PAGE = 50
MAX_OBSERVATIONS = 1000

# Rate limiting for writes (uploads + reorder)
MIN_WRITE_GAP_SECONDS = 1.1

# Client-side resize limits
RESIZE_MAX_DIM = 2048
RESIZE_QUALITY = 0.85

# OAuth
INAT_CLIENT_ID = os.environ.get("INAT_CLIENT_ID", "")
INAT_CLIENT_SECRET = os.environ.get("INAT_CLIENT_SECRET", "")
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")
