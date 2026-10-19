FROM debian:12-slim AS diagrams

RUN apt-get update \
    && apt-get install -y --no-install-recommends graphviz fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM node:22.23.2-slim AS tailwind

WORKDIR /app

RUN chown node:node /app

USER node

COPY --chown=node:node package.json package-lock.json ./
RUN npm ci

FROM tailwind AS css

COPY --chown=node:node . .
RUN npx @tailwindcss/cli -i ui/styles/app.css -o ui/static/ui/css/app.css --minify

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=css /app/ui/static/ui/css/app.css ui/static/ui/css/app.css

RUN DJANGO_SECRET_KEY=build DJANGO_CREDENTIALS_KEY=build \
    POSTGRES_DB=build POSTGRES_USER=build POSTGRES_PASSWORD=build POSTGRES_HOST=build POSTGRES_PORT=5432 \
    python manage.py collectstatic --noinput

ARG APP_UID=1000
RUN useradd --uid "${APP_UID}" --user-group --create-home --shell /usr/sbin/nologin app

USER app

EXPOSE 8000

CMD ["daphne", "--bind", "0.0.0.0", "--port", "8000", "--proxy-headers", "config.asgi:application"]
