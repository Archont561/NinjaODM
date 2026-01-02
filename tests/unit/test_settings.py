from app.config import get_settings
from app.config.settings.main import PydanticDjangoSettings


def test_settings_are_cached():
    """Test that get_settings returns the same instance."""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2  # Same object in memory
    assert id(settings1) == id(settings2)


def test_settings_instance():
    """Test that settings are properly initialized."""
    settings = get_settings()

    assert isinstance(settings, PydanticDjangoSettings)
    assert settings.APP_DIR.exists()
    assert settings.PROJECT_DIR.exists()
