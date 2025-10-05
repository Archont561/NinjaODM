import sys

from .settings.main import PROJECT_DIR, get_settings
from .settings.utils import to_django

# Add project root to path
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Create settings instance
# Export everything to Django
to_django(get_settings())
