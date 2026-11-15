import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase


def export():
    with tempfile.TemporaryDirectory() as directory:
        call_command('export_er_diagram', '--output', directory, stdout=StringIO())
        return {path.name: path.read_text(encoding='utf-8') for path in Path(directory).iterdir()}


class ExportErDiagramTests(TestCase):
    def test_writes_the_three_files_deterministically(self):
        with self.subTest('os três arquivos'):
            self.assertEqual(set(export()), {'der-conceitual.dot', 'der-fisico.dot', 'restricoes.md'})
        with self.subTest('determinístico'):
            self.assertEqual(export(), export())
