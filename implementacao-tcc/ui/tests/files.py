"""Arquivos do projeto percorridos pelos testes de texto e de classes."""

from importlib import import_module
from pathlib import Path

from django.apps import apps
from django.conf import settings

from ui import text_rules


def project_roots():
    """Diretórios dos apps do projeto e do pacote de configuração, sem bibliotecas instaladas."""
    base = Path(settings.BASE_DIR)
    roots = [Path(config.path) for config in apps.get_app_configs() if Path(config.path).is_relative_to(base)]
    roots.append(Path(import_module(settings.SETTINGS_MODULE).__file__).parent)
    return roots


def template_files(suffixes=('.html', '.txt')):
    directories = [root / 'templates' for root in project_roots()]
    directories += [Path(directory) for engine in settings.TEMPLATES for directory in engine['DIRS']]
    for directory in directories:
        if directory.is_dir():
            yield from sorted(path for path in directory.rglob('*') if path.suffix in suffixes)


def python_files():
    """Módulos do projeto, exceto testes, migrations e o text_rules, que guarda as expressões proibidas."""
    rules = Path(text_rules.__file__).resolve()
    for root in project_roots():
        for path in sorted(root.rglob('*.py')):
            parts = path.relative_to(root).parts
            if {'tests', 'migrations'} & set(parts[:-1]) or parts[-1].startswith('test'):
                continue
            if path.resolve() != rules:
                yield path


def relative(path):
    return path.relative_to(settings.BASE_DIR)
