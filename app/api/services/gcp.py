from uuid import UUID
import json
from typing import Iterable
from ninja_extra import ModelService
from django.contrib.gis.geos import Point as GEOSPoint
from django.db import transaction

from app.api.models.image import Image
from app.api.sse import emit_event


class GCPModelService(ModelService):
    def create(self, schema, **kwargs):
        image = kwargs.get("image")
        data = schema.model_dump()
        instance = self.model.objects.create(
            image=image,
            point=GEOSPoint(*data["gcp_point"], srid=4326),
            imgx=data["image_point"][0],
            imgy=data["image_point"][1],
            label=data["label"],
        )

        emit_event(
            instance.image.workspace.user_id,
            "gcp:created",
            {"uuid": str(instance.uuid), "label": instance.label},
        )
        return instance

    def update(self, instance, schema, **kwargs):
        data = schema.model_dump(exclude_unset=True)
        if "gcp_point" in data:
            instance.point = GEOSPoint(*data["gcp_point"], srid=4326)
        if "image_point" in data:
            instance.imgx, instance.imgy = data["image_point"]
        if "label" in data:
            instance.label = data["label"]
        instance.save()
        emit_event(
            instance.image.workspace.user_id,
            "gcp:updated",
            {"uuid": str(instance.uuid), "label": instance.label},
        )
        return instance

    def delete(self, instance):
        payload = {"uuid": str(instance.uuid), "label": instance.label}
        instance.delete()
        emit_event(instance.image.workspace.user_id, "gcp:deleted", payload)

    def queryset_to_geojson(self, queryset):
        qs = queryset.select_related("image").values(
            "imgx", "imgy", "label", "point", "image__uuid"
        )
        features = []
        for obj in qs:
            features.append(
                {
                    "type": "Feature",
                    "geometry": json.loads(obj["point"].geojson),
                    "properties": {
                        "label": obj["label"],
                        "image_point": [obj["imgx"], obj["imgy"]],
                        "image_uuid": str(obj["image__uuid"]),
                    },
                }
            )

        return {"type": "FeatureCollection", "features": features}

    @transaction.atomic
    def bulk_create(self, schemas: Iterable):
        instances = []

        for schema in schemas:
            data = schema.model_dump()
            instances.append(
                self.model(
                    image=Image.objects.get(uuid=data.image_uuid),
                    point=GEOSPoint(*data["gcp_point"], srid=4326),
                    imgx=data["image_point"][0],
                    imgy=data["image_point"][1],
                    label=data["label"],
                )
            )

        created = self.model.objects.bulk_create(instances)

        emit_event(
            instances[0].image.workspace.user_id,
            "gcp:bulk_created",
            {"count": len(created)},
        )
        return created

    @transaction.atomic
    def bulk_update(self, payload):
        updates = [item.model_dump(exclude_unset=True) for item in payload]
        uuids = [item["uuid"] for item in updates]

        instances = {
            str(obj.uuid): obj
            for obj in self.model.objects.filter(uuid__in=uuids)
        }

        updated_objects = []

        for item in updates:
            instance = instances.get(str(item["uuid"]))
            if not instance:
                continue

            if "gcp_point" in item:
                instance.point = GEOSPoint(*item["gcp_point"], srid=4326)

            if "image_point" in item:
                instance.imgx, instance.imgy = item["image_point"]

            if "label" in item:
                instance.label = item["label"]

            updated_objects.append(instance)

        self.model.objects.bulk_update(
            updated_objects,
            fields=["point", "imgx", "imgy", "label"],
        )

        if updated_objects:
            user_id = updated_objects[0].image.workspace.user_id
            emit_event(
                user_id,
                "gcp:bulk_updated",
                {"count": len(updated_objects)},
            )

        return updated_objects

    @transaction.atomic
    def bulk_delete(self, uuids: Iterable[UUID]):
        queryset = self.model.objects.filter(uuid__in=uuids)

        user_id = (
            queryset.first().image.workspace.user_id
            if queryset.exists()
            else None
        )

        deleted_count, _ = queryset.delete()

        if user_id:
            emit_event(
                user_id,
                "gcp:bulk_deleted",
                {"count": deleted_count},
            )

        return deleted_count
