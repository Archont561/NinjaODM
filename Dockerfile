FROM ghcr.io/prefix-dev/pixi:0.40.0

COPY . /app
WORKDIR /app

RUN pixi install -e prod

EXPOSE 8000

CMD ["pixi", "run", "-e", "prod", "scripts:runserver"]
