FROM node:22.23.2-slim AS tailwind

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ARG APP_UID=1000
RUN useradd --uid "${APP_UID}" --user-group --create-home --shell /usr/sbin/nologin app

USER app
