import json
from ninja_extra import ModelService
from django.contrib.gis.geos import Point as GEOSPoint


class GCPModelService(ModelService):

    def create(self, schema, **kwargs):
        image = kwargs.get("image")
        data = schema.model_dump()
        return self.model.objects.create(
            image=image,
            point=GEOSPoint(*data["gcp_point"], srid=4326),
            imgx=data["image_point"][0],
            imgy=data["image_point"][1],
            label=data["label"],
        )

    def update(self, instance, schema, **kwargs):
        data = schema.model_dump(exclude_unset=True)
        if "gcp_point" in data:
            instance.point = GEOSPoint(*data["gcp_point"], srid=4326)
        if "image_point" in data:
            instance.imgx, instance.imgy = data["image_point"]
        if "label" in data:
            instance.label = data["label"]
        instance.save()
        return instance
    
    def queryset_to_geojson(self, queryset):
        qs = queryset.select_related('image').values(
            'imgx', 'imgy', 'label', 'point', 'image__uuid'
        )
        features = []
        for obj in qs:
            features.append({
                "type": "Feature",
                "geometry": json.loads(obj["point"].geojson),
                "properties": {
                    "label": obj['label'],
                    "image_point": [obj['imgx'], obj['imgy']],
                    "image_uuid": str(obj['image__uuid'])
                }
            })

        return {
            "type": "FeatureCollection",
            "features": features
        }
    