FROM ghcr.io/prefix-dev/pixi:0.40.0

COPY . /app

RUN pixi install -e prod

EXPOSE 8000

CMD ["pixi", "run", "-e", "prod", "scripts:runserver"]