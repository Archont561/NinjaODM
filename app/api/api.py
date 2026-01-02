from ninja_extra import NinjaExtraAPI
from app.api.controllers.token import InternalTokenController


def create_api() -> NinjaExtraAPI:
    api = NinjaExtraAPI()
    api.register_controllers(
        InternalTokenController,
    )
    return api