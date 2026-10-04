"""Carga inicial do catálogo de permissões e dos perfis do sistema.

Os códigos são escritos literalmente, sem importar accounts.permissions, para que
a migration continue reproduzível se as constantes mudarem depois. O perfil DOCENTE
não recebe permissões e nenhuma permissão PERFIL.* é concedida.
"""

from django.db import migrations

PERMISSIONS = [
    ('AGENDA.ANALISAR', 'Consultar as solicitações de agendamento, aprovar, rejeitar e sugerir alternativa'),
    ('AGENDA.CRIAR', 'Criar solicitação de agendamento em nome de outro usuário'),
    ('AGENDA.SOLICITAR', 'Solicitar agendamento, consultar as próprias solicitações e responder à alternativa sugerida'),
    ('AGENDA.VISUALIZAR', 'Consultar a Grade da Agenda'),
    ('AUDITORIA.VISUALIZAR', 'Consultar os registros de auditoria do sistema'),
    ('CONFIGURACAO.EDITAR', 'Editar as configurações do sistema'),
    ('DISCIPLINA.CRIAR', 'Cadastrar disciplina'),
    ('DISCIPLINA.EDITAR', 'Alterar o nome de uma disciplina do próprio escopo sem uso no ensalamento'),
    ('DISCIPLINA.EXCLUIR', 'Excluir disciplina do próprio escopo sem uso no ensalamento'),
    ('DISCIPLINA.VISUALIZAR', 'Consultar as disciplinas do próprio escopo'),
    ('ENSALAMENTO.ALTERAR_RECORRENCIA', 'Alterar a recorrência de uma aula do ensalamento a partir de uma data'),
    ('ENSALAMENTO.CANCELAR_OCORRENCIA', 'Cancelar a ocorrência de qualquer aula do ensalamento numa data'),
    ('ENSALAMENTO.CRIAR_RECORRENCIA', 'Cadastrar uma aula recorrente no ensalamento'),
    ('ENSALAMENTO.ENCERRAR_RECORRENCIA', 'Encerrar uma aula do ensalamento a partir de uma data'),
    ('ENSALAMENTO.EXCLUIR_IMPORTACAO', 'Excluir importações de ensalamento descartadas ou com erros'),
    ('ENSALAMENTO.IMPORTAR', 'Importar o ensalamento de um semestre pela planilha institucional'),
    ('ENSALAMENTO.VISUALIZAR', 'Consultar a grade do ensalamento confirmado'),
    ('ESPACO.ALTERAR_SITUACAO', 'Desativar e reativar espaço, inclusive pela importação de ensalamento'),
    ('ESPACO.CRIAR', 'Cadastrar espaço, inclusive pela confirmação da importação de ensalamento'),
    ('ESPACO.EDITAR', 'Alterar o nome e os outros nomes de um espaço, inclusive pela importação de ensalamento'),
    ('ESPACO.EXCLUIR', 'Excluir espaço sem aulas no ensalamento'),
    ('ESPACO.VISUALIZAR', 'Consultar a lista de espaços'),
    ('NOTIFICACAO.PUBLICAR', 'Publicar notificações para os usuários do sistema'),
    ('PAINEL.VISUALIZAR', 'Visualizar o painel administrativo'),
    ('PERFIL.ALTERAR_PERMISSOES', 'Definir as permissões concedidas por um perfil'),
    ('PERFIL.CRIAR', 'Criar perfil personalizado'),
    ('PERFIL.EDITAR', 'Alterar nome e descrição de um perfil'),
    ('PERFIL.EXCLUIR', 'Excluir perfil personalizado sem usuários'),
    ('PERFIL.VISUALIZAR', 'Listar e consultar perfis e as permissões que concedem'),
    ('RELATORIO.VISUALIZAR', 'Visualizar os relatórios'),
    ('TURMA.CRIAR', 'Cadastrar turma de um curso'),
    ('TURMA.EDITAR', 'Alterar o rótulo de uma turma do próprio escopo sem uso no ensalamento'),
    ('TURMA.EXCLUIR', 'Excluir turma do próprio escopo sem uso no ensalamento'),
    ('TURMA.VISUALIZAR', 'Consultar as turmas do próprio escopo'),
    ('USUARIO.ALTERAR_PERFIL', 'Trocar o perfil de um usuário'),
    ('USUARIO.ALTERAR_SITUACAO', 'Desativar e reativar usuário'),
    ('USUARIO.CRIAR', 'Cadastrar usuário'),
    ('USUARIO.EDITAR', 'Alterar nome e e-mail de usuário'),
    ('USUARIO.EXCLUIR_IMPORTACAO', 'Excluir importações de usuários descartadas ou com erros'),
    ('USUARIO.IMPORTAR', 'Importar usuários por planilha e consultar o histórico das importações'),
    ('USUARIO.VISUALIZAR', 'Listar e consultar usuários'),
]

SYSTEM_ROLES = [
    ('ADMINISTRADOR', 'Administrador'),
    ('DOCENTE', 'Docente'),
]

INITIAL_GRANTS = {
    'ADMINISTRADOR': [
        'AGENDA.ANALISAR',
        'AGENDA.CRIAR',
        'AGENDA.SOLICITAR',
        'AGENDA.VISUALIZAR',
        'AUDITORIA.VISUALIZAR',
        'CONFIGURACAO.EDITAR',
        'DISCIPLINA.CRIAR',
        'DISCIPLINA.EDITAR',
        'DISCIPLINA.EXCLUIR',
        'DISCIPLINA.VISUALIZAR',
        'ENSALAMENTO.ALTERAR_RECORRENCIA',
        'ENSALAMENTO.CANCELAR_OCORRENCIA',
        'ENSALAMENTO.CRIAR_RECORRENCIA',
        'ENSALAMENTO.ENCERRAR_RECORRENCIA',
        'ENSALAMENTO.EXCLUIR_IMPORTACAO',
        'ENSALAMENTO.IMPORTAR',
        'ENSALAMENTO.VISUALIZAR',
        'ESPACO.ALTERAR_SITUACAO',
        'ESPACO.CRIAR',
        'ESPACO.EDITAR',
        'ESPACO.EXCLUIR',
        'ESPACO.VISUALIZAR',
        'NOTIFICACAO.PUBLICAR',
        'PAINEL.VISUALIZAR',
        'RELATORIO.VISUALIZAR',
        'TURMA.CRIAR',
        'TURMA.EDITAR',
        'TURMA.EXCLUIR',
        'TURMA.VISUALIZAR',
        'USUARIO.ALTERAR_PERFIL',
        'USUARIO.ALTERAR_SITUACAO',
        'USUARIO.CRIAR',
        'USUARIO.EDITAR',
        'USUARIO.EXCLUIR_IMPORTACAO',
        'USUARIO.IMPORTAR',
        'USUARIO.VISUALIZAR',
    ],
    'DOCENTE': [
        'AGENDA.SOLICITAR',
        'AGENDA.VISUALIZAR',
    ],
}

def create_catalog(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')
    RolePermission = apps.get_model('accounts', 'RolePermission')

    for code, description in PERMISSIONS:
        Permission.objects.get_or_create(code=code, defaults={'description': description})

    for code, name in SYSTEM_ROLES:
        Role.objects.get_or_create(code=code, defaults={'name': name, 'is_system': True})

    for role_code, permission_codes in INITIAL_GRANTS.items():
        role = Role.objects.get(code=role_code)
        for permission in Permission.objects.filter(code__in=permission_codes):
            RolePermission.objects.get_or_create(role=role, permission=permission)


def remove_catalog(apps, schema_editor):
    """As concessões saem por CASCADE; perfis ainda vinculados a usuários falham por PROTECT."""
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')

    Role.objects.filter(code__in=[code for code, _ in SYSTEM_ROLES], is_system=True).delete()
    Permission.objects.filter(code__in=[code for code, _ in PERMISSIONS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_catalog, remove_catalog),
    ]
