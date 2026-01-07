from typing import Any, Optional
from pydantic import BaseModel, Field, Json, PositiveFloat, PositiveInt, conint
from ninja.schema import Schema
from enum import StrEnum, unique, auto
from pathlib import Path


# ============ ENUMS ============
@unique
class OptionEnum(StrEnum):
    def __str__(self) -> str:
        return self.name.lower()


@unique
class CameraLens(OptionEnum):
    AUTO = auto()
    PERSPECTIVE = auto()
    BROWN = auto()
    FISHEYE = auto()
    FISHEYE_OPENCV = auto()
    SPHERICAL = auto()
    EQUIRECTANGULAR = auto()
    DUAL = auto()


class FeatureQuality(OptionEnum):
    ULTRA = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    LOWEST = auto()


class FeatureType(OptionEnum):
    AKAZE = auto()
    DSPSIFT = auto()
    HAHOG = auto()
    ORB = auto()
    SIFT = auto()


class MatcherType(OptionEnum):
    BOW = auto()
    BRUTEFORCE = auto()
    FLANN = auto()


class RadiometricCalibration(OptionEnum):
    NONE = auto()
    CAMERA = auto()
    CAMERA_AND_SUM = auto()


class MergeType(OptionEnum):
    ALL = auto()
    POINTCLOUD = auto()
    ORTHOPHOTO = auto()
    DEM = auto()


class PipelineStage(OptionEnum):
    DATASET = auto()
    SPLIT = auto()
    MERGE = auto()
    OPENSFM = auto()
    OPENMVS = auto()
    ODM_FILTERPOINTS = auto()
    ODM_MESHING = auto()
    MVS_TEXTURING = auto()
    ODM_GEOREFERENCING = auto()
    ODM_DEM = auto()
    ODM_ORTHOPHOTO = auto()
    ODM_REPORT = auto()
    ODM_POSTPROCESS = auto()


class SFMAlgorithm(OptionEnum):
    INCREMENTAL = auto()
    TRIANGULATION = auto()
    PLANAR = auto()


class OrthophotoCompression(OptionEnum):
    JPEG = auto()
    LZW = auto()
    PACKBITS = auto()
    DEFLATE = auto()
    LZMA = auto()
    NONE = auto()


class PointCloudQuality(OptionEnum):
    ULTRA = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    LOWEST = auto()


# ============ STAGES ============
class StageModel(BaseModel):
    model_config = {
        "extra": "forbid",
        "populate_by_name": True,
    }

    def to_odm_cli(self) -> list[str]:
        """
        Converts the set fields into a list of CLI arguments.
        Example: ['--camera-lens=auto', '--mesh-size=200000']
        """
        # exclude_unset=True ensures we only provide flags the user actually specified
        # by_alias=True ensures we use 'camera-lens' instead of 'camera_lens'
        data = self.model_dump(by_alias=True, exclude_unset=True)

        cli_args = []
        for key, value in data.items():
            # Convert booleans to lowercase 'true'/'false' strings for CLI compatibility
            if isinstance(value, bool):
                value = str(value).lower()

            # Handle cases where value might be None (though exclude_unset usually handles this)
            if value is not None:
                cli_args.append(f"--{key}={value}")

        return cli_args


class DatasetStagePublic(StageModel):
    camera_lens: CameraLens = Field(
        default=CameraLens.AUTO,
        alias="camera-lens",
        description="Camera projection model to use. 'auto' tries to detect the correct type automatically.",
    )
    cameras: Json[Any] = Field(
        default={},
        description="JSON object or path to cameras.json file containing custom camera calibration parameters from previous run.",
    )
    gps_accuracy: PositiveFloat = Field(
        default=3,
        alias="gps-accuracy",
        description="Standard deviation/uncertainty of image GPS coordinates in meters (affects georeferencing quality).",
    )
    gps_z_offset: float = Field(
        default=0,
        alias="gps-z-offset",
        description="Vertical offset (meters) to be applied to all image GPS altitudes.",
    )
    bg_removal: bool = Field(
        default=False,
        alias="bg-removal",
        description="Use AI-based background removal to automatically create masks (useful for object-focused reconstructions).",
    )
    sky_removal: bool = Field(
        default=False,
        alias="sky-removal",
        description="Use AI to automatically detect and mask out sky portions in images.",
    )


class DatasetStageInternal(DatasetStagePublic):
    use_exif: bool = Field(
        default=False,
        alias="use-exif",
        description="Force use of EXIF GPS data for georeferencing even when GCPs are present.",
    )
    video_limit: PositiveInt = Field(
        default=500,
        alias="video-limit",
        description="Maximum number of frames to extract when input contains video files (0 = extract all frames).",
    )
    video_resolution: PositiveInt = Field(
        default=4000,
        alias="video-resolution",
        description="Maximum resolution (longest side) for extracted video frames in pixels.",
    )
    primary_band: str = Field(
        default="auto",
        alias="primary-band",
        description="For multispectral datasets: band to use for reconstruction (auto, rgb, or band name/number).",
    )
    gcp: Path | None = Field(
        default=None,
        description="Path to text file containing ground control points (GCPs) in supported format.",
    )
    geo: Path | None = Field(
        default=None,
        description="Path to text file containing image geolocation information (alternative to EXIF GPS).",
    )


class SplitStageInternal(StageModel):
    sm_cluster: str | None = Field(
        default=None,
        alias="sm-cluster",
        description="URL to a running ClusterODM instance for distributed processing of split submodels.",
    )

    sm_no_align: bool = Field(
        default=False,
        alias="sm-no-align",
        description="Skip automatic alignment of submodels during split-merge reconstruction.",
    )

    split_image_groups: Path | None = Field(
        default=None,
        alias="split-image-groups",
        description="Path to JSON file defining custom image groups for controlled splitting.",
    )

    split_overlap: PositiveInt = Field(
        default=150,
        alias="split-overlap",
        description="Radius (meters) of overlap region between neighboring submodels.",
    )


class MergeStageInternal(StageModel):
    merge: MergeType = Field(
        default=MergeType.ALL,
        description="Select which components to merge when processing a split dataset.",
    )
    merge_skip_blending: bool = Field(
        default=False,
        alias="merge-skip-blending",
        description="Skip orthophoto color blending step during merge (faster, but may show seams).",
    )


class SFMStagePublic(StageModel):
    feature_quality: FeatureQuality = Field(
        default=FeatureQuality.HIGH,
        alias="feature-quality",
        description="Quality level of feature detection & extraction (higher = more features, slower).",
    )
    feature_type: FeatureType = Field(
        default=FeatureType.DSPSIFT,
        alias="feature-type",
        description="Algorithm used for keypoint detection and descriptor computation.",
    )
    matcher_type: MatcherType = Field(
        default=MatcherType.FLANN,
        alias="matcher-type",
        description="Feature matching algorithm (FLANN is usually fastest and most accurate).",
    )
    pc_quality: PointCloudQuality = Field(
        default=PointCloudQuality.MEDIUM,
        alias="pc-quality",
        description="Density/quality level of dense point cloud reconstruction.",
    )
    sfm_algorithm: SFMAlgorithm = Field(
        default=SFMAlgorithm.INCREMENTAL,
        alias="sfm-algorithm",
        description="Structure-from-Motion reconstruction algorithm to use.",
    )


class SFMStageInternal(SFMStagePublic):
    matcher_neighbors: PositiveInt = Field(
        default=0,
        alias="matcher-neighbors",
        description="Limit feature matching to N nearest images based on GPS distance (0 = auto).",
    )
    matcher_order: PositiveInt = Field(
        default=0,
        alias="matcher-order",
        description="Limit feature matching to N nearest images based on filename ordering (0 = disabled).",
    )
    min_num_features: PositiveInt = Field(
        default=10000,
        alias="min-num-features",
        description="Minimum number of features that should be detected per image.",
    )
    ignore_gsd: bool = Field(
        default=False,
        alias="ignore-gsd",
        description="Ignore estimated Ground Sampling Distance when deciding processing parameters.",
    )
    force_gps: bool = Field(
        default=False,
        alias="force-gps",
        description="Always use EXIF GPS data even when GCPs are available.",
    )
    radiometric_calibration: RadiometricCalibration = Field(
        default=RadiometricCalibration.NONE,
        alias="radiometric-calibration",
        description="Set the radiometric calibration to perform on images. When processing multispectral and thermal images you should set this option to obtain reflectance/temperature values (otherwise you will get digital number values). [camera] applies black level, vignetting, row gradient gain/exposure compensation (if appropriate EXIF tags are found) and computes absolute temperature values. [camera+sun] is experimental, applies all the corrections of [camera], plus compensates for spectral radiance registered via a downwelling light sensor (DLS) taking in consideration the angle of the sun.",
    )
    rolling_shutter: bool = Field(
        default=False,
        alias="rolling-shutter",
        description="Enable rolling shutter distortion correction (useful for fast-moving platforms).",
    )
    rolling_shutter_readout: PositiveInt = Field(
        default=0,
        alias="rolling-shutter-readout",
        description="Override rolling shutter readout time in milliseconds (0 = auto-detect).",
    )
    sfm_no_partial: bool = Field(
        default=False,
        alias="sfm-no-partial",
        description="Do not allow merging of partial/incomplete reconstructions.",
    )
    skip_band_alignment: bool = Field(
        default=False,
        alias="skip-band-alignment",
        description="Skip alignment of multispectral bands (faster but less accurate).",
    )
    use_fixed_camera_params: bool = Field(
        default=False,
        alias="use-fixed-camera-params",
        description="Disable optimization of internal camera parameters during bundle adjustment.",
    )
    use_hybrid_bundle_adjustment: bool = Field(
        default=False,
        alias="use-hybrid-bundle-adjustment",
        description="Use local bundle adjustment per image + global every ~100 images (faster on large datasets).",
    )


class FilterPointsStagePublic(StageModel):
    auto_boundary: bool = Field(
        False,
        alias="auto-boundary",
        description="Create reconstruction boundary automatically based on camera positions.",
    )

    boundary: Json[Any] = Field(
        default={},
        description="GeoJSON polygon defining the area to reconstruct (outside will be ignored).",
    )

    fast_orthophoto: bool = Field(
        False,
        alias="fast-orthophoto",
        description="Generate orthophoto directly from sparse point cloud (much faster, lower quality).",
    )


class FilterPointsStageInternal(FilterPointsStagePublic):
    auto_boundary_distance: PositiveFloat = Field(
        0,
        alias="auto-boundary-distance",
        description="Distance (meters) between camera positions and automatic boundary edge.",
    )
    pc_sample: PositiveFloat = Field(
        0,
        alias="pc-sample",
        description="Downsample point cloud by taking points no closer than N meters (0 = disabled).",
    )


class MeshingStagePublic(StageModel):
    mesh_octree_depth: conint(ge=1, le=14) = Field(
        11,
        alias="mesh-octree-depth",
        description="Depth of octree used for surface reconstruction (higher = more detail, slower).",
    )

    mesh_size: PositiveInt = Field(
        200_000,
        alias="mesh-size",
        description="Maximum number of vertices allowed in final textured mesh.",
    )


class MeshingStageInternal(MeshingStagePublic):
    skip_3dmodel: bool = Field(
        False,
        alias="skip-3dmodel",
        description="Skip generation of full 3D textured mesh model.",
    )


class TexturingStagePublic(StageModel):
    texturing_skip_global_seam_leveling: bool = Field(
        False,
        alias="texturing-skip-global-seam-leveling",
        description="Skip global color normalization across images (faster, may show seams).",
    )
    use_3dmesh: bool = Field(
        False,
        alias="use-3dmesh",
        description="Use full 3D mesh instead of 2.5D approach for orthophoto generation.",
    )


class TexturingStageInternal(TexturingStagePublic):
    texturing_keep_unseen_faces: bool = Field(
        False,
        alias="texturing-keep-unseen-faces",
        description="Keep mesh faces that are not observed by any camera (may improve mesh completeness).",
    )
    texturing_single_material: bool = Field(
        False,
        alias="texturing-single-material",
        description="Generate OBJ with single material/texture atlas instead of multiple.",
    )
    gltf: bool = Field(
        False,
        alias="gltf",
        description="Also export mesh in glTF Binary (.glb) format.",
    )


class GeoreferencingStagePublic(StageModel):
    pc_copc: bool = Field(
        False,
        alias="pc-copc",
        description="Save point cloud in Cloud Optimized Point Cloud (COPC) format.",
    )
    pc_csv: bool = Field(
        False, alias="pc-csv", description="Export point cloud also in CSV format."
    )
    pc_ept: bool = Field(
        False,
        alias="pc-ept",
        description="Export point cloud in Entwine Point Tile (EPT) format.",
    )
    pc_las: bool = Field(
        False, alias="pc-las", description="Export point cloud in LAS/LAZ format."
    )
    align: Path | None = Field(
        None,
        description="Path to DEM (GeoTIFF) or point cloud (LAS/LAZ) to align reconstruction to.",
    )


class GeoreferencingStageInternal(GeoreferencingStagePublic):
    pc_rectify: bool = Field(
        False,
        alias="pc-rectify",
        description="Apply ground rectification transformation to point cloud.",
    )
    pc_classify: bool = Field(
        False,
        alias="pc-classify",
        description="Classify point cloud into ground/non-ground using simple progressive morphological filter.",
    )
    crop: PositiveFloat = Field(
        3,
        description="Distance (meters) used to automatically crop output rasters around dataset boundary.",
    )


class DEMStagePublic(StageModel):
    dem_resolution: PositiveFloat = Field(
        5,
        alias="dem-resolution",
        description="Resolution of generated DSM/DTM in cm/pixel.",
    )
    dsm: bool = Field(
        False,
        description="Generate Digital Surface Model (includes vegetation, buildings, etc.).",
    )
    dtm: bool = Field(
        False, description="Generate Digital Terrain Model (bare-earth, ground only)."
    )


class DEMStageInternal(DEMStagePublic):
    smrf_scalar: PositiveFloat = Field(
        1.25,
        alias="smrf-scalar",
        description="Elevation scalar parameter for SMRF ground classification.",
    )
    smrf_slope: PositiveFloat = Field(
        0.15,
        alias="smrf-slope",
        description="Slope parameter (rise over run) for SMRF ground classification.",
    )
    smrf_threshold: PositiveFloat = Field(
        0.5,
        alias="smrf-threshold",
        description="Elevation threshold parameter (meters) for SMRF ground classification.",
    )
    smrf_window: PositiveFloat = Field(
        18.0,
        alias="smrf-window",
        description="Window radius (meters) for SMRF ground classification algorithm.",
    )
    dem_decimation: PositiveInt = Field(
        1,
        alias="dem-decimation",
        description="Decimation factor for point cloud before DEM generation (higher = faster, less detail).",
    )
    dem_euclidean_map: bool = Field(
        False,
        alias="dem-euclidean-map",
        description="Also generate Euclidean distance raster map for each DEM.",
    )
    dem_gapfill_steps: PositiveInt = Field(
        3,
        alias="dem-gapfill-steps",
        description="Number of gap-filling iterations when creating DEM.",
    )
    cog: bool = Field(
        False, description="Create Cloud-Optimized GeoTIFFs (COG) for DEM/DSM/DTM."
    )
    tiles: bool = Field(
        False, description="Generate web-friendly tiled format (MBTiles) for DEM/DSM."
    )


class OrthophotoStagePublic(StageModel):
    orthophoto_compression: OrthophotoCompression = Field(
        OrthophotoCompression.DEFLATE,
        alias="orthophoto-compression",
        description="Compression method used for orthophoto GeoTIFF.",
    )
    orthophoto_kmz: bool = Field(
        False,
        alias="orthophoto-kmz",
        description="Also export orthophoto as Google Earth KMZ file.",
    )
    orthophoto_png: bool = Field(
        False,
        alias="orthophoto-png",
        description="Also export orthophoto as 8-bit PNG (lossy, smaller file size).",
    )
    orthophoto_resolution: PositiveFloat = Field(
        5,
        alias="orthophoto-resolution",
        description="Resolution of orthophoto in cm/pixel.",
    )
    skip_orthophoto: bool = Field(
        False,
        alias="skip-orthophoto",
        description="Skip orthophoto generation entirely.",
    )


class OrthophotoStageInternal(OrthophotoStagePublic):
    build_overviews: bool = Field(
        False,
        alias="build-overviews",
        description="Generate pyramid overviews for faster visualization in GIS software.",
    )
    orthophoto_no_tiled: bool = Field(
        False,
        alias="orthophoto-no-tiled",
        description="Generate striped (non-tiled) GeoTIFF instead of standard tiled format.",
    )
    orthophoto_cutline: bool = Field(
        False,
        alias="orthophoto-cutline",
        description="Generate vector polygon cutline around cropped orthophoto area.",
    )


class ReportStagePublic(StageModel):
    skip_report: bool = Field(
        False,
        alias="skip-report",
        description="Skip generation of PDF report. This can save time if you don't need a report.",
    )


class PostProcessingStageInternal(StageModel):
    tiles_3d: bool = Field(
        False, alias="3d-tiles", description="Generate OGC 3D Tiles outputs"
    )
    copy_to: Optional[Path] = Field(
        None, alias="copy-to", description="Generate OGC 3D Tiles outputs"
    )


# ============ FULL ============
class ODMOptionsPublic(Schema):
    dataset: Optional[DatasetStagePublic] = None
    sfm: Optional[SFMStagePublic] = None
    filterpoints: Optional[FilterPointsStagePublic] = None
    meshing: Optional[MeshingStagePublic] = None
    texturing: Optional[TexturingStagePublic] = None
    georeferencing: Optional[GeoreferencingStagePublic] = None
    dem: Optional[DEMStagePublic] = None
    orthophoto: Optional[OrthophotoStagePublic] = None
    report: Optional[ReportStagePublic] = None

    model_config = {"extra": "forbid"}


class ODMOptionsInternal(Schema):
    dataset: Optional[DatasetStageInternal] = None
    split: Optional[SplitStageInternal] = None
    merge: Optional[MergeStageInternal] = None
    sfm: Optional[SFMStageInternal] = None
    filterpoints: Optional[FilterPointsStageInternal] = None
    meshing: Optional[MeshingStageInternal] = None
    texturing: Optional[TexturingStageInternal] = None
    georeferencing: Optional[GeoreferencingStageInternal] = None
    dem: Optional[DEMStageInternal] = None
    orthophoto: Optional[OrthophotoStageInternal] = None
    report: Optional[ReportStagePublic] = None
    postprocess: Optional[PostProcessingStageInternal] = None

    model_config = {"extra": "forbid"}
