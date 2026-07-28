# app.py
from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime
import logging
import math
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# iNaturalist API base URL
INATURALIST_API = "https://api.inaturalist.org/v1/observations"
PER_PAGE = 50  # Observations per page


def format_id_with_delimiters(id_value, delimiter='-', pattern='every3'):
    """
    Format an ID with delimiters based on user preferences.

    Args:
        id_value: The ID string to format
        delimiter: Character to use as delimiter (default: '-')
        pattern: Pattern for delimiter placement ('every3', 'every4', 'every2')

    Returns:
        Formatted ID string with delimiters
    """
    if not id_value:
        return id_value

    id_str = str(id_value)

    if pattern == 'every3':
        # Place delimiter after every 3 characters from the right
        parts = [id_str[max(0, i - 3):i] for i in range(len(id_str), 0, -3)]
        parts.reverse()
        return delimiter.join(parts)
    elif pattern == 'every4':
        # Place delimiter after every 4 characters from the right
        parts = [id_str[max(0, i - 4):i] for i in range(len(id_str), 0, -4)]
        parts.reverse()
        return delimiter.join(parts)
    elif pattern == 'every2':
        # Place delimiter after every 2 characters from the right
        parts = [id_str[max(0, i - 2):i] for i in range(len(id_str), 0, -2)]
        parts.reverse()
        return delimiter.join(parts)
    else:
        return id_str


def get_photo_url(observation):
    """Extract the first photo URL from an observation."""
    photos = observation.get('photos', [])
    if photos and len(photos) > 0:
        # Get the square thumbnail (smallest) for better performance
        photo = photos[0]
        # Try to get the square URL first, fall back to original
        for size in ['square', 'small', 'medium', 'large', 'original']:
            if size in photo:
                return photo[size]
        # If no size key found, try to get the URL directly
        return photo.get('url', '')
    return ''


def format_observed_date(observed_on, observed_on_details=None):
    """Format the observed date with timestamp if available."""
    if not observed_on:
        return 'N/A'

    try:
        # If we have detailed time information
        if observed_on_details:
            # Try to parse the datetime from details
            date_str = observed_on_details.get('date', observed_on)
            time_str = observed_on_details.get('time', '')
            time_zone = observed_on_details.get('time_zone', 'UTC')

            if time_str:
                # Try to parse full datetime
                try:
                    dt = datetime.fromisoformat(f"{date_str}T{time_str}")
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

        # Fallback: just format the date
        dt = datetime.strptime(observed_on, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except:
        return observed_on


@app.route('/')
def index():
    """Render the main page with filters."""
    return render_template('index.html', per_page=PER_PAGE)


@app.route('/search', methods=['GET'])
def search_observations():
    """Search iNaturalist observations based on provided filters with pagination."""
    try:
        # Get filter parameters from request
        username = request.args.get('username', '').strip()
        taxon = request.args.get('taxon', '').strip()
        date_start = request.args.get('date_start', '').strip()
        date_end = request.args.get('date_end', '').strip()
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

        # Build API query parameters
        params = {
            'per_page': PER_PAGE,
            'page': page,
            'quality_grade': 'research,needs_id'
        }

        if username:
            params['user_login'] = username

        if taxon:
            params['taxon_name'] = taxon

        # Handle date filtering
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
        if sort_by == 'observed_on':
            params['order_by'] = 'observed_on'
        elif sort_by == 'id':
            params['order_by'] = 'id'
        elif sort_by == 'taxon':
            params['order_by'] = 'taxon'
        elif sort_by == 'user':
            params['order_by'] = 'user'
        elif sort_by == 'place_guess':
            params['order_by'] = 'place_guess'
        else:
            params['order_by'] = 'observed_on'

        params['order'] = 'desc' if sort_order == 'desc' else 'asc'

        # Make API request
        response = requests.get(INATURALIST_API, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        observations = data.get('results', [])
        total_results = data.get('total_results', 0)

        # Calculate pagination info
        total_pages = math.ceil(total_results / PER_PAGE) if total_results > 0 else 0

        # Format observations for display
        formatted_observations = []
        for obs in observations:
            try:
                # Get taxon information
                taxon_data = obs.get('taxon', {})
                taxon_rank = taxon_data.get('rank', 'Unknown')

                # Get photo URL
                photo_url = get_photo_url(obs)

                # Format observation date with time
                observed_on = obs.get('observed_on', 'N/A')
                observed_on_details = obs.get('observed_on_details', {})
                formatted_date = format_observed_date(observed_on, observed_on_details)

                formatted_obs = {
                    'id': obs.get('id'),
                    'taxon_name': taxon_data.get('name', 'Unknown'),
                    'taxon_rank': f"{taxon_rank}",
                    'observed_on': observed_on,
                    'observed_on_formatted': formatted_date,
                    'place_guess': obs.get('place_guess', 'Unknown location'),
                    'user_login': obs.get('user', {}).get('login', 'Unknown'),
                    'url': obs.get('uri'),
                    'quality_grade': obs.get('quality_grade', 'N/A'),
                    'iconic_taxon_name': taxon_data.get('iconic_taxon_name', 'Unknown'),
                    'photo_url': photo_url,
                    'photos_count': len(obs.get('photos', []))
                }
                formatted_observations.append(formatted_obs)
            except Exception as e:
                logging.warning(f"Error formatting observation {obs.get('id')}: {e}")
                continue

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
        logging.error(f"API Request error: {e}")
        return jsonify({
            'success': False,
            'error': f"Error connecting to iNaturalist API: {str(e)}"
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
