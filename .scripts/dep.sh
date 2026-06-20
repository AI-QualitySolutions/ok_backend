#!/bin/bash
set -e

echo "Deployment started ..."

# Pull the latest version of the app
echo "Pulling the latest changes from the repository..."
git pull origin company
echo "New changes copied to server!"

# Activate Virtual Environment
# Syntax: source venv/bin/activate
echo "Activating Virtual Environment..."
source venv/bin/activate
echo "Virtual env 'venv' activated!"

# Clear Cache (Custom management commands)
echo "Clearing Python bytecode (.pyc) files and cache..."
python manage.py clean_pyc
python manage.py clear_cache

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt --no-input

# Collect static files
echo "Serving static files..."
python manage.py collectstatic --noinput

# Apply database migrations
echo "Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Deactivate Virtual Environment
echo "Deactivating Virtual Environment..."
deactivate
echo "Virtual env 'venv' deactivated!"

# Reload and restart system services
echo "Reloading system services..."
sudo systemctl daemon-reload
sudo systemctl restart hajjc
sudo systemctl restart hajjc.socket hajjc.service

# Test and restart Nginx
echo "Testing Nginx configuration and restarting..."
sudo nginx -t && sudo systemctl restart nginx

echo "Deployment completed successfully!"
