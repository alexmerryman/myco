from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime, timedelta
import logging
import math

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# iNaturalist API v2 base URL
INATURALIST_API_V2 = "https://api.inaturalist.org/v2/observations"
PER_PAGE = 50  # Observations per page
MAX_OBSERVATIONS = 1000  # Maximum observations to show on initial load

# v2 uses 'fields' parameter with dot notation for nested fields
# Format: field1,field2,nested.field1,nested.field2
FIELDS_TO_RETURN = [
    'id',
    'uri',
    'observed_on',
    'time_observed_at',
    'observed_time_zone',
    'place_guess',
    'quality_grade',
    'latitude',
    'longitude',
    'positional_accuracy',
    'taxon.id',
    'taxon.name',
    'taxon.rank',
    'taxon.rank_level',
    'taxon.preferred_common_name',
    'taxon.iconic_taxon_name',
    'user.id',
    'user.login',
    'user.name',
    'observation_photos.photo.id',
    'observation_photos.photo.url',
    'observation_photos.photo.square',
    'observation_photos.photo.medium',
    'observation_photos.photo.large',
    'observation_photos.photo.original'
]


def format_id_with_delimiters(id_value, delimiter='-', pattern='every3'):
    """Format an ID with delimiters based on user preferences."""
    if not id_value:
        return id_value

    id_str = str(id_value)

    if pattern == 'every3':
        parts = [id_str[max(0, i - 3):i] for i in range(len(id_str), 0, -3)]
        parts.reverse()
        return delimiter.join(parts)
    elif pattern == 'every4':
        parts = [id_str[max(0, i - 4):i] for i in range(len(id_str), 0, -4)]
        parts.reverse()
        return delimiter.join(parts)
    elif pattern == 'every2':
        parts = [id_str[max(0, i - 2):i] for i in range(len(id_str), 0, -2)]
        parts.reverse()
        return delimiter.join(parts)
    else:
        return id_str


def get_photo_url(observation, size='square'):
    """Extract a photo URL from an observation at the specified size."""
    photos = []

    if 'observation_photos' in observation:
        for obs_photo in observation.get('observation_photos', []):
            if 'photo' in obs_photo:
                photos.append(obs_photo['photo'])

    if not photos and 'photos' in observation:
        photos = observation.get('photos', [])

    if photos and len(photos) > 0:
        photo = photos[0]

        if size in photo:
            return photo[size]

        url = photo.get('url', '')
        if url:
            if '?size=' in url:
                url = url.split('?size=')[0]
            elif '&size=' in url:
                url = url.split('&size=')[0]
            return url

        for size_key in ['original', 'large', 'medium', 'small', 'square']:
            if size_key in photo:
                return photo[size_key]

    return ''


def get_full_size_photo_url(observation: dict):
    """Get the full-size/original photo URL from an observation."""
    photos = []

    if 'observation_photos' in observation:
        for obs_photo in observation.get('observation_photos', []):
            if 'photo' in obs_photo:
                photos.append(obs_photo['photo'])

    if not photos and 'photos' in observation:
        photos = observation.get('photos', [])

    if photos and len(photos) > 0:
        photo = photos[0]
        url = photo.get('url', '')
        if url:
            url = url.replace("square.jpg", "large.jpg")
            return url

    return ''


def format_observed_date(time_observed_at: str, observed_time_zone: str, observed_on: str) -> str:
    """Format the observed date with timestamp if available."""
    if not time_observed_at:
        return 'N/A'

    try:
        dt_obj = datetime.fromisoformat(time_observed_at)
        dt_str_simple = dt_obj.strftime('%Y-%m-%d %I:%M:%S %p')
        dt_str = f"{dt_str_simple} ({observed_time_zone})"
        return dt_str
    except:
        return observed_on


@app.route('/')
def index():
    """Render the main page with filters."""
    return render_template('index.html', per_page=PER_PAGE)


@app.route('/search', methods=['GET'])
def search_observations():
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

        # Add taxon filter
        if taxon:
            params['taxon_name'] = taxon

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
        app.logger.info(f"API Request URL: {INATURALIST_API_V2}")
        app.logger.info(f"Request params: {params}")

        # Make API request to v2 endpoint
        response = requests.get(INATURALIST_API_V2, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Log the response for debugging
        app.logger.info(f"Response status: {response.status_code}")
        app.logger.info(f"Response keys: {list(data.keys())}")
        if 'results' in data and len(data['results']) > 0:
            app.logger.info(f"First result keys: {list(data['results'][0].keys())}")

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
                app.logger.warning(f"Error formatting observation {obs.get('id', 'unknown')}: {e}")
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
        app.logger.error(f"API Request error: {e}")
        return jsonify({
            'success': False,
            'error': f"Error connecting to iNaturalist API: {str(e)}"
        }), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
