from django.test import TestCase
from config.testing import IsolatedCasesMixin
from django.urls import reverse

from accounts import permissions
from accounts.models import User
from accounts.tests.roles import requester_role, role_with
from tutorials.catalog import (
    AGENDA_REQUEST, AGENDA_REVIEW, NOTIFICATIONS, PANEL, PERSONAL_INFO, SPACES, TIMETABLE_IMPORT, USERS, USERS_IMPORT, features,
)

PASSWORD = 'Senha-forte-123'


def slugs(response):
    return [entry['feature'].slug for module in response.context['modules'] for entry in module['features']]


class HelpCenterTests(IsolatedCasesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superadmin = User.objects.create_superadmin('root@ifnmg.edu.br', 'Root', PASSWORD)
        cls.requester = User.objects.register(email='ana@ifnmg.edu.br', name='Ana Souza', role=requester_role())

    def user_with(self, *codes):
        role = role_with('_'.join(code.replace('.', '_') for code in codes) or 'VAZIO', *codes)
        return User.objects.register(email=f'{role.code.lower()}@ifnmg.edu.br', name='Pessoa', role=role)

    def get(self, user):
        self.client.force_login(user)
        return self.client.get(reverse('help_center'))

    def contextual(self, user, screen):
        self.client.force_login(user)
        return self.client.get(reverse('help_center'), {'tela': screen})

    def test_funcionalidades_seguem_as_permissoes(self):
        with self.case('quem solicita'):
            response = self.get(self.requester)
            self.assertEqual(response.status_code, 200)
            visible = slugs(response)
            self.assertIn(AGENDA_REQUEST.slug, visible)
            self.assertIn(NOTIFICATIONS.slug, visible)
            self.assertNotIn(USERS.slug, visible)
        with self.case('sem permissão fora do HTML'):
            response = self.get(self.requester)
            self.assertNotContains(response, USERS.title)
            self.assertNotContains(response, f'tutorials/{USERS.slug}/')
            self.assertNotContains(response, reverse('user_list'))
        with self.case('sem permissões'):
            response = self.get(self.user_with())
            self.assertEqual(slugs(response), [NOTIFICATIONS.slug, PERSONAL_INFO.slug])
        with self.case('superadmin'):
            response = self.get(self.superadmin)
            self.assertEqual(slugs(response), [feature.slug for feature in features()])
        with self.case('passos'):
            response = self.get(self.user_with(permissions.SPACE_VIEW))
            entry = next(
                entry for module in response.context['modules'] for entry in module['features']
                if entry['feature'].slug == SPACES.slug
            )
            self.assertEqual(
                [item['desktop'] for item in entry['steps']],
                [SPACES.image(1, 'computador'), SPACES.image(4, 'computador')],
            )
            self.assertNotContains(response, SPACES.steps[1].text)
        with self.case('sem passo liberado'):
            response = self.get(self.user_with(permissions.PANEL_VIEW))
            self.assertNotIn(PANEL.slug, slugs(response))

    def test_imagens_e_botao_do_fim(self):
        with self.case('imagens'):
            response = self.get(self.requester)
            step = AGENDA_REQUEST.steps[0]
            self.assertContains(response, f'alt="{step.alt}"')
            self.assertContains(response, f'/static/{AGENDA_REQUEST.image(1, "celular")}')
            self.assertContains(response, f'/static/{AGENDA_REQUEST.image(1, "computador")}')
        with self.case('botão do fim'):
            response = self.get(self.requester)
            self.assertContains(response, f'href="{reverse(AGENDA_REQUEST.screen)}"')

    def test_link_da_ajuda_leva_a_tela_de_origem(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse('agenda_my_requests'))
        self.assertContains(response, f'href="{reverse("help_center")}?tela=agenda_my_requests"', count=2)

    def test_ajuda_da_tela(self):
        with self.case('só as da tela'):
            response = self.contextual(self.requester, 'agenda_my_requests')
            visible = [entry['feature'].slug for entry in response.context['entries']]
            self.assertIn(AGENDA_REQUEST.slug, visible)
            self.assertNotIn(NOTIFICATIONS.slug, visible)
            self.assertNotIn(AGENDA_REVIEW.slug, visible)
            self.assertNotContains(response, 'id="indice"')
            self.assertNotContains(response, NOTIFICATIONS.title)
            self.assertEqual(response.context['screen_url'], reverse('agenda_grid'))
        with self.case('segue as permissões'):
            response = self.contextual(self.superadmin, 'space_allocation_grid')
            self.assertEqual(
                [entry['feature'].slug for entry in response.context['entries']],
                [feature.slug for feature in response.context['screen'].features],
            )
            self.assertIn(TIMETABLE_IMPORT, response.context['screen'].features)
            response = self.contextual(self.user_with(permissions.USER_IMPORT), 'user_import_list')
            self.assertEqual([entry['feature'] for entry in response.context['entries']], [USERS_IMPORT])
            self.assertEqual(response.context['screen_url'], reverse('user_import_list'))
        with self.case('tela fora do menu'):
            for screen in ('profile', 'profile_password'):
                with self.subTest(screen=screen):
                    response = self.contextual(self.requester, screen)
                    self.assertEqual([entry['feature'] for entry in response.context['entries']], [PERSONAL_INFO])
                    self.assertEqual(response.context['screen_label'], 'Informações pessoais')
                    self.assertEqual(response.context['screen_url'], reverse('profile'))
        with self.case('sem ajuda liberada'):
            response = self.contextual(self.requester, 'audit_log_list')
            self.assertEqual(response.context['entries'], [])
            self.assertContains(response, 'Nenhuma ajuda desta tela liberada para o seu perfil.')
        with self.case('tela desconhecida'):
            for screen in ('', 'home', 'inexistente', 'help_center'):
                with self.subTest(screen=screen):
                    response = self.contextual(self.requester, screen)
                    self.assertNotIn('screen', response.context)
                    self.assertIn(NOTIFICATIONS.slug, slugs(response))

    def test_navegacao_entre_funcionalidades(self):
        with self.case('lista as liberadas'):
            response = self.get(self.requester)
            self.assertContains(response, 'data-guide-nav')
            self.assertContains(response, f'<a class="guide-nav-link" href="#{AGENDA_REQUEST.slug}">{AGENDA_REQUEST.title}</a>', html=True)
            self.assertNotContains(response, f'href="#{USERS.slug}"')
        with self.case('só com mais de uma'):
            self.assertContains(self.contextual(self.requester, 'agenda_grid'), 'data-guide-nav')
            self.assertNotContains(self.contextual(self.superadmin, 'spaces_list'), 'data-guide-nav')
