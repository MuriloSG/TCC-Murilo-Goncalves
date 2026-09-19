"""Verificação do texto exibido em todos os templates e módulos Python do projeto."""

import re
from importlib import import_module
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.test import Client, SimpleTestCase, TestCase

from accounts.models import Role, User
from ui import text_rules
from ui.text_rules import find_violations, html_fragments, python_fragments, template_fragments


def project_roots():
    """Diretórios dos apps do projeto e do pacote de configuração, sem bibliotecas instaladas."""
    base = Path(settings.BASE_DIR)
    roots = [Path(config.path) for config in apps.get_app_configs() if Path(config.path).is_relative_to(base)]
    roots.append(Path(import_module(settings.SETTINGS_MODULE).__file__).parent)
    return roots


def template_files():
    directories = [root / 'templates' for root in project_roots()]
    directories += [Path(directory) for engine in settings.TEMPLATES for directory in engine['DIRS']]
    for directory in directories:
        if directory.is_dir():
            yield from sorted(path for path in directory.rglob('*') if path.suffix in ('.html', '.txt'))


def python_files():
    """Módulos do projeto, exceto testes, migrations e o text_rules.

    O text_rules fica de fora porque guarda as expressões proibidas como dado.
    """
    rules = Path(text_rules.__file__).resolve()
    for root in project_roots():
        for path in sorted(root.rglob('*.py')):
            parts = path.relative_to(root).parts
            if {'tests', 'migrations'} & set(parts[:-1]) or parts[-1].startswith('test'):
                continue
            if path.resolve() != rules:
                yield path


def describe(label, fragments):
    return [
        f'{label}:{fragment.line}: "{fragment.text}" → "{violation.excerpt}". {violation.guidance}'
        for fragment in fragments
        for violation in find_violations(fragment.text, fragment.element)
    ]


class ProjectTextTests(SimpleTestCase):
    def assertNoViolations(self, problems):
        if problems:
            self.fail(f'{len(problems)} violação(ões) das regras de texto:\n' + '\n'.join(problems))

    def test_templates_seguem_as_regras_de_texto(self):
        files = list(template_files())
        self.assertTrue(any(path.name == 'user_list.html' for path in files))
        self.assertTrue(any(path.name == 'logged_out.txt' for path in files))
        problems = []
        for path in files:
            fragments = template_fragments(path.read_text(encoding='utf-8'), path.name)
            problems += describe(path.relative_to(settings.BASE_DIR), fragments)
        self.assertNoViolations(problems)

    def test_modulos_python_seguem_as_regras_de_texto(self):
        files = list(python_files())
        self.assertTrue(any(path.name == 'views.py' for path in files))
        self.assertFalse(any('tests' in path.parts or 'migrations' in path.parts for path in files))
        problems = []
        for path in files:
            problems += describe(path.relative_to(settings.BASE_DIR), python_fragments(path.read_text(encoding='utf-8')))
        self.assertNoViolations(problems)


class TemplateExtractionTests(SimpleTestCase):
    def violations(self, source, name='page.html'):
        return describe(name, template_fragments(source, name))

    def test_exclamacao_em_texto_visivel_indica_linha_e_trecho(self):
        source = '{% extends "base.html" %}\n{% block content %}\n  <p>Usuário cadastrado!</p>\n{% endblock %}\n'
        self.assertEqual(
            self.violations(source),
            ['page.html:3: "Usuário cadastrado!" → "!". Sem ponto de exclamação.'],
        )

    def test_operador_em_tag_e_doctype_nao_sao_texto(self):
        source = '<!DOCTYPE html>\n<html>{% if a != b %}<p>Texto.</p>{% endif %}<!-- Olá! --></html>'
        self.assertEqual(self.violations(source), [])

    def test_comentarios_do_django_nao_sao_texto(self):
        source = '{# Olá! #}<p>Texto.</p>{% comment %}Olá!{% endcomment %}'
        self.assertEqual(self.violations(source), [])

    def test_variavel_vira_marcador_neutro(self):
        self.assertEqual(self.violations('<h1>{{ action|capfirst }} usuário</h1>'), [])
        self.assertEqual(self.violations('<h1>{{ action|capfirst }} {{ target.name }}?</h1>'), [])

    def test_maiusculas_no_titulo_do_bloco(self):
        source = '{% extends "base.html" %}{% block title %}Cadastrar Usuário{% endblock %}'
        self.assertEqual(len(self.violations(source)), 1)

    def test_maiusculas_consideram_o_elemento_inteiro(self):
        self.assertEqual(len(self.violations('<button><svg></svg> <span>Excluir Perfil</span></button>')), 1)
        self.assertEqual(self.violations('<p>Leia o <strong>Manual</strong>.</p>'), [])

    def test_atributos_visiveis(self):
        self.assertEqual(len(self.violations('<button aria-label="Bloquear"></button>')), 1)
        self.assertEqual(len(self.violations('<input placeholder="Informe o email">')), 1)
        self.assertEqual(len(self.violations('<input type="submit" value="Salvar Dados">')), 1)
        self.assertEqual(self.violations('<input type="email" name="email">'), [])

    def test_template_txt_e_todo_visivel(self):
        self.assertEqual(
            self.violations('{% autoescape off %}Olá.\n\n{{ link }}{% endautoescape %}', 'message.txt'),
            ['message.txt:1: "Olá." → "Olá". Sem saudação.'],
        )


class PythonExtractionTests(SimpleTestCase):
    def violations(self, source):
        return describe('views.py', python_fragments(source))

    def test_mensagem_proibida_indica_modulo_e_linha(self):
        source = (
            'from django.contrib import messages\n'
            '\n'
            'def perform(request):\n'
            '    messages.success(request, "Perfil criado com sucesso.")\n'
        )
        self.assertEqual(
            self.violations(source),
            ['views.py:4: "Perfil criado com sucesso." → "com sucesso". Sem "com sucesso". Informe o fato no particípio.'],
        )

    def test_docstring_nao_e_texto_exibido(self):
        source = '"""Módulo simples."""\n\nclass A:\n    """Uma classe simples."""\n\n    def b(self):\n        """Simples."""\n'
        self.assertEqual(self.violations(source), [])

    def test_logger_nao_e_texto_exibido(self):
        self.assertEqual(self.violations('logger.exception("Algo deu errado com %s.", email)\n'), [])

    def test_fstring_e_chaves_sem_espaco(self):
        self.assertEqual(len(self.violations('x = f"Usuário {email} bloqueado."\n')), 1)
        self.assertEqual(self.violations('x = {"email": 1}\ny = f"Usuário {data[\'email\']} desativado."\n'), [])


class RenderedPagesTextTests(TestCase):
    """Percorre as telas renderizadas, com os textos do Django e do allauth.

    A regra de maiúsculas não é aplicada aqui, porque as telas trazem nomes de
    pessoas e perfis. Ela é verificada nos templates.
    """

    @classmethod
    def setUpTestData(cls):
        cls.teacher = Role.objects.get(code='DOCENTE')
        cls.admin = User.objects.create_superadmin(
            email='admin@ifnmg.edu.br', name='Ana Souza', password='Senha-forte-123',
        )
        cls.target = User.objects.register(email='maria@ifnmg.edu.br', name='Maria Sousa', role=cls.teacher)
        cls.role = Role.objects.create_role(code='COORDENACAO', name='Coordenação', permissions=[])

    def setUp(self):
        cache.clear()

    def assertPageFollowsRules(self, response):
        problems = describe(response.request['PATH_INFO'], [
            fragment._replace(element=None) for fragment in html_fragments(response.content.decode())
        ])
        self.assertEqual(problems, [])

    def test_telas_de_gestao(self):
        self.client.force_login(self.admin)
        for url in (
            '/inicio/', '/usuarios/', '/usuarios/novo/',
            f'/usuarios/{self.target.pk}/editar/', f'/usuarios/{self.target.pk}/perfil/',
            f'/usuarios/{self.target.pk}/desativar/', f'/usuarios/{self.target.pk}/reativar/',
            '/perfis/', '/perfis/novo/', f'/perfis/{self.role.pk}/', f'/perfis/{self.role.pk}/editar/',
            f'/perfis/{self.role.pk}/permissoes/', f'/perfis/{self.role.pk}/excluir/',
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertPageFollowsRules(response)
        response = self.client.post('/usuarios/novo/', {'name': '', 'email': 'invalido', 'role': ''})
        self.assertPageFollowsRules(response)

    def test_pagina_de_acesso_negado(self):
        self.client.force_login(self.target)
        response = self.client.get('/usuarios/')
        self.assertEqual(response.status_code, 403)
        self.assertPageFollowsRules(response)

    def test_telas_de_login_e_senha(self):
        client = Client()
        for url in ('/contas/login/', '/contas/senha/recuperar/', '/contas/senha/recuperar/enviado/',
                    '/contas/senha/redefinir/concluido/', '/contas/senha/redefinir/1-invalido/'):
            with self.subTest(url=url):
                self.assertPageFollowsRules(client.get(url, follow=True))
        self.assertPageFollowsRules(client.post('/contas/login/', {'login': 'invalido', 'password': 'x'}))
        self.assertPageFollowsRules(client.post('/contas/login/', {'login': 'admin@ifnmg.edu.br', 'password': 'x'}))
        self.assertPageFollowsRules(client.post('/contas/senha/recuperar/', {'email': 'invalido'}))
        client.post('/contas/senha/recuperar/', {'email': 'maria@ifnmg.edu.br'})
        for number, line in enumerate(mail.outbox[0].body.splitlines(), start=1):
            self.assertEqual(find_violations(line), [], f'Linha {number} do e-mail: {line}')
        link = re.search(r'http://testserver(/contas/senha/redefinir/\S+/)', mail.outbox[0].body).group(1)
        response = client.get(link, follow=True)
        self.assertPageFollowsRules(response)
        response = client.post(response.request['PATH_INFO'], {'password1': 'Senha-forte-123', 'password2': 'Outra-senha-456'})
        self.assertPageFollowsRules(response)
        self.assertPageFollowsRules(client.post(response.request['PATH_INFO'], {'password1': '123', 'password2': '123'}))

    def test_logout(self):
        self.client.force_login(self.admin)
        self.assertPageFollowsRules(self.client.get('/contas/logout/'))
        self.assertPageFollowsRules(self.client.post('/contas/logout/', follow=True))
