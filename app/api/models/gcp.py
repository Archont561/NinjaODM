from django.contrib.gis.db import models as geo_models
from app.api.models.mixins import UUIDPrimaryKeyModelMixin
from app.api.models.image import Image


class GroundControlPoint(UUIDPrimaryKeyModelMixin, geo_models.Model):
    point = geo_models.PointField(srid=4326, dim=3)
    label = geo_models.CharField(max_length=255)
    image = geo_models.ForeignKey(
        Image,
        related_name="gcps",
        on_delete=geo_models.CASCADE,
    )

    class Meta:
        verbose_name = "Ground control point"
        verbose_name_plural = "Ground control points"
        # Unique labels for GCP per image: (image, label) must be unique
        constraints = [
            geo_models.UniqueConstraint(
                fields=["image", "label"],
                name="unique_gcp_label_per_image",
            )
        ]

    def __str__(self) -> str:
        return f"{self.label} ({self.lng:.6f}, {self.lat:.6f}, {self.alt:.2f})"

    @property
    def lng(self) -> float:
        return self.point.x

    @property
    def lat(self) -> float:
        return self.point.y

    @property
    def alt(self) -> float:
        return self.point.z

    def to_odm_repr(self) -> str:
        """
        Return one line in OpenDroneMap GCP format:

        {lng} {lat} {alt} {image name} {label}
        """
        return f"{self.lng:.8f} {self.lat:.8f} {self.alt:.3f} {self.image.name} {self.label}"
    