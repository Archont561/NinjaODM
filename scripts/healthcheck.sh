#!/bin/bash
set -e

# Health check script for Docker container
# Checks if the Django application is responding

# Configuration
HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-http://localhost:8000/api/health}"
TIMEOUT="${HEALTH_TIMEOUT:-5}"
MAX_RETRIES="${HEALTH_RETRIES:-3}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Function to log messages
log_info() {
    echo -e "${GREEN}[HEALTH]${NC} $1"
}

log_error() {
    echo -e "${RED}[HEALTH ERROR]${NC} $1" >&2
}

# Function to check health using curl
check_with_curl() {
    local http_code
    http_code=$(curl -f -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$HEALTH_ENDPOINT" 2>/dev/null || echo "000")

    if [ "$http_code" = "200" ]; then
        return 0
    else
        log_error "HTTP status code: $http_code"
        return 1
    fi
}

# Function to check health using Python (fallback)
check_with_python() {
    python -c "
import urllib.request
import sys

try:
    response = urllib.request.urlopen('$HEALTH_ENDPOINT', timeout=$TIMEOUT)
    if response.status == 200:
        sys.exit(0)
    else:
        print(f'HTTP status: {response.status}', file=sys.stderr)
        sys.exit(1)
except urllib.error.HTTPError as e:
    print(f'HTTP error: {e.code}', file=sys.stderr)
    sys.exit(1)
except urllib.error.URLError as e:
    print(f'Connection error: {e.reason}', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'Health check failed: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1
}

# Main health check logic with retries
retry=0
while [ $retry -lt "$MAX_RETRIES" ]; do
    if command -v curl &> /dev/null; then
        if check_with_curl; then
            log_info "Health check passed (curl) - Attempt $((retry + 1))/$MAX_RETRIES"
            exit 0
        fi
    else
        if check_with_python; then
            log_info "Health check passed (python) - Attempt $((retry + 1))/$MAX_RETRIES"
            exit 0
        fi
    fi

    retry=$((retry + 1))
    if [ $retry -lt "$MAX_RETRIES" ]; then
        log_error "Health check failed, retrying... ($retry/$MAX_RETRIES)"
        sleep 1
    fi
done

log_error "Health check failed after $MAX_RETRIES attempts"
exit 1
