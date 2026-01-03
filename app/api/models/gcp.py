from django.contrib.gis.db import models as geo_models
from app.api.models.mixins import UUIDPrimaryKeyModelMixin
from app.api.models.image import Image


class GroundControlPoint(UUIDPrimaryKeyModelMixin, geo_models.Model):
    # World coordinates (WGS84, 3D)
    point = geo_models.PointField(srid=4326, dim=3)

    # Image coordinates (pixel space)
    imgx = geo_models.FloatField(help_text="X coordinate in image (pixels)")
    imgy = geo_models.FloatField(help_text="Y coordinate in image (pixels)")

    label = geo_models.CharField(max_length=50)
    image = geo_models.ForeignKey(
        Image,
        related_name="gcps",
        on_delete=geo_models.CASCADE,
    )

    class Meta:
        verbose_name = "Ground control point"
        verbose_name_plural = "Ground control points"
        constraints = [
            geo_models.UniqueConstraint(
                fields=["image", "label"],
                name="unique_gcp_label_per_image",
            ),
            geo_models.CheckConstraint(
                condition=geo_models.Q(imgx__gte=0) & geo_models.Q(imgy__gte=0),
                name="gcp_img_coordinates_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.label} "
            f"(lng={self.lng:.6f}, lat={self.lat:.6f}, alt={self.alt:.2f}, "
            f"imgx={self.imgx:.1f}, imy={self.imy:.1f})"
        )

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

        {lng} {lat} {alt} {imgx} {imy} {image name} {label}
        """
        return (
            f"{self.lng:.8f} "
            f"{self.lat:.8f} "
            f"{self.alt:.3f} "
            f"{self.imgx:.3f} "
            f"{self.imy:.3f} "
            f"{self.image.name} "
            f"{self.label}"
        )
    