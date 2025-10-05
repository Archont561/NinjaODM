# Build stage: use Pixi image to install dependencies and build environment
FROM ghcr.io/prefix-dev/pixi:0.55.0-jammy-cuda-12.9.1 AS build

ARG ENVIRONMENT=prod

WORKDIR /workspace

# Copy dependency files first (better layer caching)
COPY pixi.lock pyproject.toml ./

# Install dependencies into /workspace/.pixi
RUN pixi install -e $ENVIRONMENT

# Create the shell-hook bash script to activate the environment
RUN pixi shell-hook -e $ENVIRONMENT > /shell-hook.sh && \
    echo 'exec "$@"' >> /shell-hook.sh

# Copy application code
COPY app ./app
COPY scripts ./scripts


# Runtime stage
FROM ubuntu:24.04 AS runtime

ARG ENVIRONMENT=prod
ENV ENVIRONMENT=$ENVIRONMENT

WORKDIR /workspace
ENV PYTHONPATH=/workspace

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user and group
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --create-home --shell /bin/bash appuser

# Copy environment and activation script from build stage
# Note: prefix path must stay the same as in build container
COPY --from=build /workspace/.pixi/envs/$ENVIRONMENT /workspace/.pixi/envs/$ENVIRONMENT
COPY --from=build /shell-hook.sh /shell-hook.sh

# Copy application code
COPY --from=build /workspace/app ./app
COPY --from=build /workspace/scripts ./scripts
COPY --from=build /workspace/pyproject.toml ./

# Set ownership to non-root user
RUN chown -R appuser:appuser /workspace

# Switch to non-root user
USER appuser

# Healthcheck configuration
ENV HEALTH_ENDPOINT=http://localhost:8000/api/health
ENV HEALTH_TIMEOUT=5

EXPOSE 8000

# Configure Docker healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/workspace/scripts/healthcheck.sh"]

# Activate environment and run command
ENTRYPOINT ["/bin/bash", "/shell-hook.sh"]

# CMD in shell form for $ENVIRONMENT to be expanded
CMD bash /workspace/scripts/start.sh "$ENVIRONMENT"
