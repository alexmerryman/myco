#!/bin/bash
# start.sh - Startup script for Linux/Mac

#source .venv/bin/activate

echo "Starting iNat Viewer Flask App..."

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=dev
export FLASK_DEBUG=1
export SECRET_KEY=dev-secret-key-change-in-production

# Check if we should use production mode
if [ "$1" == "--prod" ]; then
    echo "Starting in PROD mode..."
    export FLASK_ENV=prod
    export FLASK_DEBUG=0
    gunicorn --workers 4 --bind 0.0.0.0:5000 wsgi:app
else
    echo "Starting in DEVELOPMENT mode..."
    flask run --host=127.0.0.1 --port=5000
fi

#TODO
#chmod +x start.sh
#./start.sh          # Development mode
#./start.sh --prod  # Production mode