import pytest
from unittest.mock import MagicMock
from tusclient.client import TusClient
from django_tus.signals import tus_upload_finished_signal


@pytest.fixture
def use_test_cache(settings, temp_media):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }


@pytest.mark.django_db
@pytest.mark.usefixtures("use_test_cache")
class TestWorkspaceTusUpload:

    @pytest.fixture
    def workspace(self, workspace_factory):
        return workspace_factory(user_id=999)

    def test_tus_full_upload_flow(self, live_server, workspace, temp_image_file, valid_token):

        init_url = f"{live_server.url}/api/workspaces/{workspace.uuid}/upload-images-tus/"

        client = TusClient(init_url, headers={
            "Authorization": f"Bearer {valid_token}"
        })

        signal_mock = MagicMock()
        tus_upload_finished_signal.connect(signal_mock)

        uploader = client.uploader(
            file_stream=temp_image_file.file,
            chunk_size=1500,
            retries=1,
            retry_delay=0
        )

        while uploader.offset < uploader.get_file_size():
            uploader.upload_chunk()

        assert signal_mock.called
        args, kwargs = signal_mock.call_args
        assert kwargs["workspace"] == workspace
        tus_upload_finished_signal.disconnect(signal_mock)
