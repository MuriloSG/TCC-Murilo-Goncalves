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
