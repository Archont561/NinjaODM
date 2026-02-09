from ninja_extra import api_controller, http_get, ControllerBase
from injector import inject

from app.api.schemas.token import TokenPairResponseInternal
from app.api.models.service import AuthorizedService
from app.api.services.token import TokenService

@api_controller("/demo", tags=["public", "demo"])
class DemoController(ControllerBase):  
    @inject
    def __init__(self, token_service: TokenService):
        self.token_service = token_service

    @http_get(
        "/create-demo-jwt",
        response=TokenPairResponseInternal,
        operation_id="createDemoJWT",
    ) 
    def obtain_demo_token(self, user_id: str):
        return self.token_service.obtain_token({ "user_id": user_id, "scopes": ["all"] })
    

    @http_get(
        "/create-demo-service",
        operation_id="createDemoJWT",
    )
    def create_demo_service(self):
        service = AuthorizedService.objects.create(name="DEMO SERVICE")
        return {
            "name": service.name,
            "api_key": service.api_key,
            "api_secret": service.api_secret,
        }