from uuid import UUID
from typing import Optional, Tuple, Annotated
from datetime import datetime
from geojson_pydantic import Feature, Point, FeatureCollection
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo
from ninja import ModelSchema, Schema, FilterSchema, FilterLookup
from ninja_schema.orm.utils.converter import convert_django_field
from django.contrib.gis.db.models import PointField

from app.api.models.gcp import GroundControlPoint


@convert_django_field.register(PointField)
def convert_point_field(field, **kwargs) -> Tuple[type, FieldInfo]:
    """Convert GeoDjango PointField to Pydantic tuple type."""
    if field.null:
        return (Optional[Tuple[float, float, float]], Field(default=None))
    return (Tuple[float, float, float], Field(...))


class GCPCreate(Schema):
    image_uuid: str
    gcp_point: Tuple[float, float, float]  # (lng, lat, alt)
    image_point: Tuple[float, float]  # (imgx, imgy)
    label: str


class GCPUpdate(Schema):
    gcp_point: Optional[Tuple[float, float, float]] = None
    image_point: Optional[Tuple[float, float]] = None
    label: Optional[str] = None


class GCPResponse(ModelSchema):
    image_uuid: UUID = Field(..., alias="image.uuid")
    gcp_point: Tuple[float, float, float]
    image_point: Tuple[float, float]

    class Meta:
        model = GroundControlPoint
        fields = [
            "uuid",
            "created_at",
            "label",
        ]

    @staticmethod
    def resolve_gcp_point(obj: GroundControlPoint):
        return (obj.lng, obj.lat, obj.alt)

    @staticmethod
    def resolve_image_point(obj: GroundControlPoint):
        return (obj.imgx, obj.imgy)


class GCPProperties(BaseModel):
    image_uuid: UUID
    image_point: Tuple[float, float]
    label: str


GCPFeature = Feature[Point, GCPProperties]
GCPFeatureCollection = FeatureCollection[GCPFeature]


class GCPFilterSchema(FilterSchema):
    label: Annotated[Optional[str], FilterLookup("label__icontains")] = None
    created_after: Annotated[Optional[datetime], FilterLookup("created_at__gte")] = None
    created_before: Annotated[Optional[datetime], FilterLookup("created_at__lte")] = (
        None
    )
    image_uuid: Annotated[Optional[UUID], FilterLookup("image__uuid")] = None
    workspace_uuid: Annotated[
        Optional[UUID], FilterLookup("image__workspace__uuid")
    ] = None


class GCPBaseSSEData(Schema):
    uuid: UUID
    label: str


class GPCCreatedSSEData(GCPBaseSSEData): ...


class GCPUpdatedSSEData(GCPBaseSSEData): ...


class GCPDeletedSSEData(GCPBaseSSEData): ...
