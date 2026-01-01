from ninja_extra import NinjaExtraAPI


def create_api() -> NinjaExtraAPI:
    api = NinjaExtraAPI()
    api.auto_discover_controllers()
    return api
