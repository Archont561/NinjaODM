# Build stage: use Pixi image to install dependencies and build environment
FROM ghcr.io/prefix-dev/pixi:0.40.0 AS build

WORKDIR /workspace

# ARG to specify pixi environment, default to prod
ARG ENVIRONMENT=prod

# Copy pixi configuration files first for better caching
COPY pyproject.toml pixi.lock* ./

# Install the specified pixi environment
RUN pixi install -e ${ENVIRONMENT}

# Copy application source
COPY ./app ./app

# Copy scripts
COPY ./scripts ./scripts

# ------------------------------------------------------------

# Runtime stage: MINIMAL Ubuntu image
FROM ubuntu:24.04 AS runtime

# Build arguments
ARG ENVIRONMENT=prod

# Environment variables
ENV ENVIRONMENT=${ENVIRONMENT} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /workspace

# Install ONLY essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user and group
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home --shell /bin/bash appuser

# Copy pixi binary from build stage
COPY --from=build /usr/local/bin/pixi /usr/local/bin/pixi

# Copy the COMPLETE Pixi environment (includes GDAL, GEOS, PROJ, Python, etc.)
COPY --from=build /workspace/.pixi/envs/${ENVIRONMENT} /workspace/.pixi/envs/${ENVIRONMENT}

# Copy pixi project files (needed for pixi to work)
COPY --from=build /workspace/pyproject.toml /workspace/pixi.lock* ./

# Copy application source
COPY --chown=appuser:appuser ./app ./app

# Copy scripts
COPY --from=build --chown=appuser:appuser /workspace/scripts ./scripts

# Set executable permissions on scripts
RUN chmod +x ./scripts/*.sh

# Create necessary directories with correct permissions
RUN mkdir -p /workspace/data /workspace/static /workspace/media \
    && chown -R appuser:appuser /workspace

# Switch to non-root user
USER appuser
ENV HOME=/home/appuser

# Expose default port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/workspace/scripts/healthcheck.sh"]

# Entrypoint
ENTRYPOINT ["/workspace/scripts/entrypoint.sh"]