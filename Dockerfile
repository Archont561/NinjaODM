# Use Pixi base image
FROM ghcr.io/prefix-dev/pixi:0.40.0

# Install bash (if not already in base image)
RUN apt-get update && apt-get install -y bash \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m pixiuser

# Set working directory
WORKDIR /app

# ----------------------------
# 1. Copy only dependency files first
# ----------------------------
COPY pyproject.toml pixi.lock /app/

# Install Pixi dependencies for production
RUN pixi install -e prod

# ----------------------------
# 2. Copy the rest of the app
# ----------------------------
COPY . /app

# Ensure logs folder exists and permissions
RUN mkdir -p /app/app/logs \
    && chown -R pixiuser:pixiuser /app/app

# Make start script executable
RUN chmod +x /app/scripts/start.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV PIXI_ENVIRONMENT=prod

# Expose port
EXPOSE 8000

# Switch to non-root user
USER pixiuser

# ----------------------------
# 3. Start production via Bash
# ----------------------------
CMD ["pixi", "run", "-e", "prod", "scripts:runserver"]
