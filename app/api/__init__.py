from ninja_extra import NinjaExtraAPI
from .auth.controllers import InternalTokenController

def create_api() -> NinjaExtraAPI:
    api = NinjaExtraAPI()
    api.register_controllers(InternalTokenController)
    return api
