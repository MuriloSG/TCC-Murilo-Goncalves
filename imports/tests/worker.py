"""Auxiliares que pedem uma operação e rodam o worker em seguida, como a tela e o worker fazem juntos.

A definição usada pelo teste é a registrada durante a execução, para que o estado que o
teste guarda nela, como a recusa da confirmação, chegue ao worker.
"""

from unittest import mock

from imports import registry
from imports.models import Import
from imports.worker import process_next


def run_worker(*definitions):
    with mock.patch.dict(registry._definitions, {definition.kind: definition for definition in definitions}):
        while process_next():
            pass


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
