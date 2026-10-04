"""Itens do menu lateral, na ordem em que aparecem.

A mesma lista decide a página aberta depois do login: é o primeiro item que o
perfil do usuário libera.
"""

from dataclasses import dataclass

from django.urls import reverse


@dataclass(frozen=True)
class MenuItem:
    """Item do menu com as rotas possíveis, cada uma com a permissão que a libera.

    A primeira rota liberada é a do link, e `prefix` marca o item como atual. A permissão de
    uma rota pode ser uma tupla, quando ela exige todas.
    """

    label: str
    icon: str
    prefix: str
    routes: tuple

    def url_for(self, user):
        """URL da primeira rota liberada ao usuário, ou None quando nenhuma é."""
        for permission, url_name in self.routes:
            if all(user.has_perm(code) for code in (permission if isinstance(permission, tuple) else (permission,))):
                return reverse(url_name)
        return None


@dataclass(frozen=True)
class MenuGroup:
    """Grupo do menu com submenu, como "Relatórios" (D8 da Change gerar-mapa-de-calor-dos-espacos).

    O grupo é só organização visual: não tem permissão própria, aparece quando algum item dele
    está liberado e mostra apenas os itens liberados, cada um pela sua permissão. O link do grupo
    é o do primeiro item liberado, e o grupo fica aberto quando um dos seus itens é o atual.
    """

    label: str
    icon: str
    items: tuple

    def entries_for(self, user):
        """Itens liberados ao usuário, como pares (item, url)."""
        return [(item, url) for item in self.items if (url := item.url_for(user))]

    def url_for(self, user):
        entries = self.entries_for(user)
        return entries[0][1] if entries else None


MENU = (
    MenuItem('Painel', 'layout-dashboard', 'panel', (('PAINEL.VISUALIZAR', 'panel'),)),
    MenuItem('Agenda', 'calendar-clock', 'agenda_', (('AGENDA.VISUALIZAR', 'agenda_grid'),)),
    MenuGroup('Gestão acadêmica', 'table', (
        MenuItem('Ensalamento', 'calendar-check', 'space_allocation_', (
            ('ENSALAMENTO.VISUALIZAR', 'space_allocation_grid'),
            ('ENSALAMENTO.IMPORTAR', 'space_allocation_import_list'),
        )),
        MenuItem('Espaços', 'door-open', 'spaces_', (('ESPACO.VISUALIZAR', 'spaces_list'),)),
        MenuItem('Disciplinas', 'graduation-cap', 'subjects_', (('DISCIPLINA.VISUALIZAR', 'subjects_list'),)),
        MenuItem('Turmas', 'school', 'class_groups_', (('TURMA.VISUALIZAR', 'class_groups_list'),)),
    )),
    MenuGroup('Relatórios', 'chart-column', (
        MenuItem('Mapa de calor', 'grid-3x3', 'report_heatmap', ((('RELATORIO.VISUALIZAR', 'ENSALAMENTO.VISUALIZAR'), 'report_heatmap'),)),
        MenuItem('Solicitações', 'inbox', 'report_requests', ((('RELATORIO.VISUALIZAR', 'AGENDA.ANALISAR'), 'report_requests'),)),
    )),
    MenuItem('Notificações', 'bell', 'notice_', (('NOTIFICACAO.PUBLICAR', 'notice_list'),)),
    MenuGroup('Administração', 'lock', (
        MenuItem('Usuários', 'users', 'user_', (('USUARIO.VISUALIZAR', 'user_list'),)),
        MenuItem('Perfis e permissões', 'shield-check', 'role_', (('PERFIL.VISUALIZAR', 'role_list'),)),
        MenuItem('Auditoria', 'scroll-text', 'audit_', (('AUDITORIA.VISUALIZAR', 'audit_log_list'),)),
    )),
    MenuGroup('Configurações', 'wrench', (
        MenuItem('E-mail', 'mail', 'settings_email', (('CONFIGURACAO.EDITAR', 'settings_email'),)),
    )),
)


def menu_for(user):
    """Itens liberados ao usuário, como pares (item, url), na ordem do menu."""
    entries = []
    for item in MENU:
        url = item.url_for(user)
        if url:
            entries.append((item, url))
    return entries


def first_url_for(user):
    """URL do primeiro item do menu liberado ao usuário, ou None."""
    entries = menu_for(user)
    return entries[0][1] if entries else None
