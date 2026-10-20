from django.test import TestCase
from django.urls import reverse

from accounts import permissions
from accounts.models import User
from accounts.tests.roles import requester_role, role_with
from tutorials.catalog import (
    AGENDA_REQUEST, AGENDA_REVIEW, NOTIFICATIONS, PANEL, SPACES, TIMETABLE_IMPORT, USERS, USERS_IMPORT, features,
)

PASSWORD = 'Senha-forte-123'


def slugs(response):
    return [entry['feature'].slug for module in response.context['modules'] for entry in module['features']]


class HelpCenterTests(TestCase):
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

    def test_quem_solicita_ve_a_agenda_e_o_uso_geral(self):
        response = self.get(self.requester)
        self.assertEqual(response.status_code, 200)
        visible = slugs(response)
        self.assertIn(AGENDA_REQUEST.slug, visible)
        self.assertIn(NOTIFICATIONS.slug, visible)
        self.assertNotIn(USERS.slug, visible)

    def test_funcionalidade_sem_permissao_nao_chega_ao_html(self):
        response = self.get(self.requester)
        self.assertNotContains(response, USERS.title)
        self.assertNotContains(response, f'tutorials/{USERS.slug}/')
        self.assertNotContains(response, reverse('user_list'))

    def test_sem_permissoes_so_o_uso_geral(self):
        response = self.get(self.user_with())
        self.assertEqual(slugs(response), [NOTIFICATIONS.slug])

    def test_superadmin_ve_todas_as_funcionalidades(self):
        response = self.get(self.superadmin)
        self.assertEqual(slugs(response), [feature.slug for feature in features()])

    def test_passos_seguem_a_permissao_de_cada_um(self):
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

    def test_funcionalidade_sem_passo_liberado_fica_de_fora(self):
        response = self.get(self.user_with(permissions.PANEL_VIEW))
        self.assertNotIn(PANEL.slug, slugs(response))

    def test_imagens_com_texto_alternativo_e_versao_do_celular(self):
        response = self.get(self.requester)
        step = AGENDA_REQUEST.steps[0]
        self.assertContains(response, f'alt="{step.alt}"')
        self.assertContains(response, f'/static/{AGENDA_REQUEST.image(1, "celular")}')
        self.assertContains(response, f'/static/{AGENDA_REQUEST.image(1, "computador")}')

    def test_botao_do_fim_abre_a_tela_da_funcionalidade(self):
        response = self.get(self.requester)
        self.assertContains(response, f'href="{reverse(AGENDA_REQUEST.screen)}"')

    def test_link_da_ajuda_leva_a_tela_de_origem(self):
        self.client.force_login(self.requester)
        response = self.client.get(reverse('agenda_my_requests'))
        self.assertContains(response, f'href="{reverse("help_center")}?tela=agenda_my_requests"', count=2)

    def contextual(self, user, screen):
        self.client.force_login(user)
        return self.client.get(reverse('help_center'), {'tela': screen})

    def test_ajuda_da_tela_mostra_so_as_funcionalidades_dela(self):
        response = self.contextual(self.requester, 'agenda_my_requests')
        visible = [entry['feature'].slug for entry in response.context['entries']]
        self.assertIn(AGENDA_REQUEST.slug, visible)
        self.assertNotIn(NOTIFICATIONS.slug, visible)
        self.assertNotIn(AGENDA_REVIEW.slug, visible)
        self.assertNotContains(response, 'id="indice"')
        self.assertNotContains(response, NOTIFICATIONS.title)
        self.assertEqual(response.context['screen_url'], reverse('agenda_grid'))

    def test_ajuda_da_tela_segue_as_permissoes(self):
        response = self.contextual(self.superadmin, 'space_allocation_grid')
        self.assertEqual(
            [entry['feature'].slug for entry in response.context['entries']],
            [feature.slug for feature in response.context['screen'].features],
        )
        self.assertIn(TIMETABLE_IMPORT, response.context['screen'].features)
        response = self.contextual(self.user_with(permissions.USER_IMPORT), 'user_import_list')
        self.assertEqual([entry['feature'] for entry in response.context['entries']], [USERS_IMPORT])
        self.assertEqual(response.context['screen_url'], reverse('user_import_list'))

    def test_tela_sem_ajuda_liberada_mostra_o_aviso(self):
        response = self.contextual(self.requester, 'audit_log_list')
        self.assertEqual(response.context['entries'], [])
        self.assertContains(response, 'Nenhuma ajuda desta tela liberada para o seu perfil.')

    def test_sem_tela_conhecida_mostra_a_central_completa(self):
        for screen in ('', 'home', 'inexistente', 'help_center'):
            with self.subTest(screen=screen):
                response = self.contextual(self.requester, screen)
                self.assertNotIn('screen', response.context)
                self.assertIn(NOTIFICATIONS.slug, slugs(response))

    def test_navegacao_lista_as_funcionalidades_liberadas(self):
        response = self.get(self.requester)
        self.assertContains(response, 'data-guide-nav')
        self.assertContains(response, f'<a class="guide-nav-link" href="#{AGENDA_REQUEST.slug}">{AGENDA_REQUEST.title}</a>', html=True)
        self.assertNotContains(response, f'href="#{USERS.slug}"')

    def test_ajuda_da_tela_so_tem_navegacao_com_mais_de_uma_funcionalidade(self):
        self.assertContains(self.contextual(self.requester, 'agenda_grid'), 'data-guide-nav')
        self.assertNotContains(self.contextual(self.superadmin, 'spaces_list'), 'data-guide-nav')
