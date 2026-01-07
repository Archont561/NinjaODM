import sys
import django.dispatch
from .settings.mixins.base import PROJECT_DIR
from .settings.main import get_settings
from .settings.utils import to_django, is_linting_context, setup_loguru

# Monkeypatch Django Signal to support older libraries like django-tus
# that still pass the removed 'providing_args' argument.
_old_init = django.dispatch.Signal.__init__


def _new_init(self, providing_args=None, use_caching=False):
    return _old_init(self, use_caching=use_caching)


django.dispatch.Signal.__init__ = _new_init

# Add project root to path
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Create settings instance
settings = get_settings()

# Export everything to Django
to_django(settings)

if not is_linting_context():
    try:
        from dj_easy_log import load_loguru

        # Load Loguru
        load_loguru(
            globals(),
            loglevel=settings.LOGURU_CONSOLE_LEVEL.upper(),
            configure_func=lambda instance, _: setup_loguru(instance, settings),
        )
    except (IOError, ValueError, OSError) as e:
        import warnings

        warnings.warn(
            f"Loguru setup skipped (running in linting/testing context): {e.__class__.__name__}: {e}",
            RuntimeWarning,
            stacklevel=2,
        )
