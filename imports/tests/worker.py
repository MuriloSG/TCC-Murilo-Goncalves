"""Auxiliares que pedem uma operação e rodam o worker em seguida, com a definição registrada no teste."""

from unittest import mock
from urllib.parse import urlsplit

from django.urls import resolve, reverse

from imports import registry
from imports.models import Import
from imports.worker import process_next


def run_worker(*definitions):
    with mock.patch.dict(registry._definitions, {definition.kind: definition for definition in definitions}):
        while process_next():
            pass


def poll(client, url):
    """Faz a consulta de andamento que o detalhe da importação faria depois de o worker terminar."""
    match = resolve(urlsplit(url).path)
    if match.url_name and match.url_name.endswith('_detail'):
        client.get(reverse(match.url_name.removesuffix('_detail') + '_status', kwargs=match.kwargs))


def preview(definition, rows, file_name, executor):
    importation = Import.objects.request_preview(definition, rows, file_name, executor)
    run_worker(definition)
    importation.refresh_from_db()
    return importation


def refresh(importation, definition, executor):
    importation.request_refresh(executor)
    run_worker(definition)
    importation.refresh_from_db()
    return importation.status


def confirm(importation, definition, executor):
    importation.request_confirmation(definition, executor)
    run_worker(definition)
    importation.refresh_from_db()
    return importation.status == Import.Status.CONCLUDED
