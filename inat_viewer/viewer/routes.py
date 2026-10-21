from flask import (
    Blueprint, render_template, request, jsonify, current_app,
)
import requests
import math
from datetime import datetime, timedelta

from config import (
    INATURALIST_API_V2, PER_PAGE, MAX_OBSERVATIONS,
)
from inat_api import (
    get_photo_url, get_full_size_photo_url, format_observed_date,
    get_taxon_id_from_name,
)

viewer_bp = Blueprint(
    "viewer",
    __name__,
    template_folder="templates",   # viewer/templates/index.html
)

FIELDS_TO_RETURN = [
    "id", "uri", "observed_on", "time_observed_at", "observed_time_zone",
    "place_guess", "quality_grade", "latitude", "longitude", "positional_accuracy",
    "taxon.id", "taxon.name", "taxon.rank", "taxon.rank_level",
    "taxon.preferred_common_name", "taxon.iconic_taxon_name",
    "user.id", "user.login", "user.name",
    "observation_photos.photo.id", "observation_photos.photo.url",
    "observation_photos.photo.square", "observation_photos.photo.medium",
    "observation_photos.photo.large", "observation_photos.photo.original",
]


@viewer_bp.route("/")
def index():
    return render_template("index.html", per_page=PER_PAGE,
                           max_observations=MAX_OBSERVATIONS)


@viewer_bp.route("/search")
def search():
    """Search iNaturalist observations using v2 API with provided filters and pagination."""
    try:
        # Get filter parameters from request
        username = request.args.get('username', '').strip()
        taxon = request.args.get('taxon', '').strip()
        project_id = request.args.get('project_id', '').strip()  # Filter observations by project ID
        date_start = request.args.get('date_start', '').strip()  # Filter observations by start date # TODO inclusive?
        date_end = request.args.get('date_end', '').strip()      # Filter observations by end date  # TODO inclusive?
        page = int(request.args.get('page', 1))
        sort_by = request.args.get('sort_by', 'observed_on')
        sort_order = request.args.get('sort_order', 'desc')

        # ID display options
        id_display = request.args.get('id_display', 'plain')
        id_delimiter = request.args.get('id_delimiter', '-')
        id_pattern = request.args.get('id_pattern', 'every3')

        # Validate page number
        if page < 1:
            page = 1

        # Build API v2 query parameters
        params = {
            'per_page': PER_PAGE,
            'page': page,
            'quality_grade': 'research,needs_id',
            # v2 uses 'fields' parameter to specify which fields to return
            'fields': ','.join(FIELDS_TO_RETURN)
        }

        # If no filters are applied, limit to MAX_OBSERVATIONS
        has_filters = any([username, taxon, project_id, date_start, date_end])

        # If no filters, limit the total results to MAX_OBSERVATIONS
        # by setting a date range for the most recent observations
        if not has_filters:
            # Get observations from the last 90 days to limit results
            # This is a soft limit - the API will return up to MAX_OBSERVATIONS
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            params['d1'] = start_date
            params['d2'] = end_date
            params['order_by'] = 'observed_on'
            params['order'] = 'desc'

        # Add user filter (v2 can use either user_id or user_login)
        if username:
            params['user_login'] = username

        # Add taxon filter - include all descendants
        if taxon:
            # First, try to get the taxon ID from the name
            taxon_id = get_taxon_id_from_name(taxon)
            if taxon_id:
                # Use taxon_id with the taxon_id_exclusive flag to include all descendants
                # Setting taxon_id_exclusive=true means "include this taxon and all descendants"
                params['taxon_id'] = taxon_id
                params['taxon_id_exclusive'] = True
                current_app.logger.info(f"Using taxon_id={taxon_id} with exclusive=true for taxon '{taxon}'")
            else:
                # Fallback: use taxon_name (exact match only)
                params['taxon_name'] = taxon
                current_app.logger.warning(f"Could not find taxon ID for '{taxon}', falling back to taxon_name")

        # Filter by Project ID
        if project_id:
            try:
                # Try to convert to int to validate
                project_id_int = int(project_id)
                params['project_id'] = project_id_int
            except ValueError:
                # If not a valid integer, pass as string
                params['project_id'] = project_id

        # Filter by Date
        if has_filters:
            if date_start:
                try:
                    start_date = datetime.strptime(date_start, '%Y-%m-%d')
                    params['d1'] = start_date.strftime('%Y-%m-%d')
                except ValueError:
                    pass

            if date_end:
                try:
                    end_date = datetime.strptime(date_end, '%Y-%m-%d')
                    params['d2'] = end_date.strftime('%Y-%m-%d')
                except ValueError:
                    pass

        # Add sorting
        sort_mapping = {
            'observed_on': 'observed_on',
        }
        params['order_by'] = sort_mapping.get(sort_by, 'observed_on')
        params['order'] = 'desc' if sort_order == 'desc' else 'asc'

        # Log the request for debugging
        current_app.logger.info(f"API Request URL: {INATURALIST_API_V2}")
        current_app.logger.info(f"Request params: {params}")

        # Make API request to v2 endpoint
        response = requests.get(INATURALIST_API_V2, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Log the response for debugging
        current_app.logger.info(f"Response status: {response.status_code}")
        current_app.logger.info(f"Response keys: {list(data.keys())}")
        if 'results' in data and len(data['results']) > 0:
            current_app.logger.info(f"First result keys: {list(data['results'][0].keys())}")

        # v2 API returns results in the 'results' field
        observations = data.get('results', [])
        total_results = data.get('total_results', 0)

        # If no filters, cap the total results to MAX_OBSERVATIONS
        if not has_filters and total_results > MAX_OBSERVATIONS:
            total_results = MAX_OBSERVATIONS

        # Calculate pagination info
        total_pages = math.ceil(total_results / PER_PAGE) if total_results > 0 else 0

        # Format observations for display
        formatted_observations = []
        for obs in observations:
            try:
                # Get taxon information
                taxon_data = obs.get('taxon', {})
                taxon_rank = taxon_data.get('rank', 'Unknown')

                # Get photo URLs (thumbnail and full-size)
                photo_url_thumbnail = get_photo_url(obs, 'square')
                photo_url_full = get_full_size_photo_url(obs)

                # Format observation date with time
                observed_on = obs.get('observed_on', 'N/A')
                time_observed_at = obs.get('time_observed_at', 'N/A')
                observed_time_zone = obs.get('observed_time_zone', 'N/A')
                formatted_date = format_observed_date(
                    time_observed_at=time_observed_at,
                    observed_time_zone=observed_time_zone,
                    observed_on=observed_on,
                )

                # Get user info
                user_data = obs.get('user', {})
                user_login = user_data.get('login', 'Unknown')

                # Get place guess (location)
                place_guess = obs.get('place_guess', 'Unknown location')

                # Get URI
                uri = obs.get('uri', '')

                # Get iconic taxon name
                iconic_taxon_name = taxon_data.get('iconic_taxon_name', 'Unknown')

                formatted_obs = {
                    'id': obs.get('id'),
                    'taxon_name': taxon_data.get('name', 'Unknown'),
                    'common_name': taxon_data.get('preferred_common_name', 'N/A'),
                    'taxon_rank': taxon_rank,
                    'observed_on': observed_on,
                    'observed_on_formatted': formatted_date,
                    'place_guess': place_guess,
                    'user_login': user_login,
                    'user_id': user_data.get('id'),
                    'url': uri,
                    'iconic_taxon_name': iconic_taxon_name,
                    'photo_url': photo_url_thumbnail,
                    'photo_url_full': photo_url_full,
                    'photos_count': len(obs.get('photos', [])) or len(obs.get('observation_photos', [])),
                    'latitude': obs.get('latitude'),
                    'longitude': obs.get('longitude'),
                    'positional_accuracy': obs.get('positional_accuracy')
                }
                formatted_observations.append(formatted_obs)
            except Exception as e:
                current_app.logger.warning(f"Error formatting observation {obs.get('id', 'unknown')}: {e}")
                continue

        # If no filters and we have more results than MAX_OBSERVATIONS, truncate
        if not has_filters and len(formatted_observations) > MAX_OBSERVATIONS:
            formatted_observations = formatted_observations[:MAX_OBSERVATIONS]
            total_results = MAX_OBSERVATIONS
            total_pages = math.ceil(total_results / PER_PAGE) if total_results > 0 else 0

        return jsonify({
            'success': True,
            'count': len(formatted_observations),
            'total_results': total_results,
            'observations': formatted_observations,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'per_page': PER_PAGE,
                'has_next': page < total_pages,
                'has_prev': page > 1
            },
            'filters_applied': {
                'username': username if username else 'None',
                'taxon': taxon if taxon else 'None',
                'project_id': project_id if project_id else 'None',
                'date_start': date_start if date_start else 'None',
                'date_end': date_end if date_end else 'None',
                'sort_by': sort_by,
                'sort_order': sort_order
            },
            'id_display_options': {
                'display': id_display,
                'delimiter': id_delimiter,
                'pattern': id_pattern
            }
        })

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"API Request error: {e}")
        return jsonify({
            'success': False,
            'error': f"Error connecting to iNaturalist API: {str(e)}"
        }), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }), 500
