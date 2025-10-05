#!/bin/bash
set -e

# Health check script for Docker container
# Checks if the Django application is responding

# Configuration
HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-http://localhost:8000/api/health}"
TIMEOUT="${HEALTH_TIMEOUT:-5}"

# Function to check health using curl
check_with_curl() {
    curl -f -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$HEALTH_ENDPOINT" | grep -q "200"
}

# Function to check health using Python
check_with_python() {
    python -c "
import urllib.request
import sys

try:
    response = urllib.request.urlopen('$HEALTH_ENDPOINT', timeout=$TIMEOUT)
    if response.status == 200:
        sys.exit(0)
    sys.exit(1)
except Exception as e:
    print(f'Health check failed: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# Try curl first (faster), fall back to Python
if command -v curl &> /dev/null; then
    if check_with_curl; then
        exit 0
    else
        echo "Health check failed via curl" >&2
        exit 1
    fi
else
    if check_with_python; then
        exit 0
    else
        echo "Health check failed via Python" >&2
        exit 1
    fi
fi