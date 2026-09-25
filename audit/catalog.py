"""Catálogo das ações, dos módulos e das origens da auditoria (D4).

Ação, módulo e origem são gravados como código e só ganham rótulo na interface.
Incluir uma ação é acrescentar a constante e o rótulo dela aqui, sem migration de
esquema e sem estrutura de log própria. O ponto único de gravação recusa um
código que não esteja neste catálogo.

O termo exibido para o campo `resource` é "módulo", e não "recurso", porque o
glossário da seção 9.4 das convenções reserva "recurso" ao espaço reservável.
"""

LOGIN = 'LOGIN'
LOGIN_REFUSED = 'LOGIN_RECUSADO'
LOGOUT = 'SAIDA'
PASSWORD_REQUESTED = 'SENHA_SOLICITADA'
PASSWORD_RESET = 'SENHA_REDEFINIDA'
ACCESS = 'ACESSO'
CREATE = 'CRIAR'
UPDATE = 'ALTERAR'
DELETE = 'EXCLUIR'
ACTIVATE = 'ATIVAR'
DEACTIVATE = 'DESATIVAR'
IMPORT = 'IMPORTAR'
DISCARD = 'DESCARTAR'
EXPORT = 'EXPORTAR'
PUBLISH = 'PUBLICAR'
SEND = 'ENVIAR'
FAIL = 'FALHAR'

ACTION_LABELS = {
    LOGIN: 'Entrada',
    LOGIN_REFUSED: 'Entrada recusada',
    LOGOUT: 'Saída',
    PASSWORD_REQUESTED: 'Recuperação de senha solicitada',
    PASSWORD_RESET: 'Senha redefinida',
    ACCESS: 'Acesso',
    CREATE: 'Cadastro',
    UPDATE: 'Alteração',
    DELETE: 'Exclusão',
    ACTIVATE: 'Reativação',
    DEACTIVATE: 'Desativação',
    IMPORT: 'Importação',
    DISCARD: 'Descarte',
    EXPORT: 'Exportação',
    PUBLISH: 'Publicação',
    SEND: 'Envio',
    FAIL: 'Falha no envio',
}

AUTHENTICATION = 'AUTENTICACAO'
USER = 'USUARIO'
ROLE = 'PERFIL'
USER_IMPORT = 'IMPORTACAO_USUARIO'
SPACE_ALLOCATION_IMPORT = 'IMPORTACAO_ENSALAMENTO'
EMAIL = 'EMAIL'
AUDIT = 'AUDITORIA'
NOTICE = 'NOTIFICACAO'
SPACE = 'ESPACO'

RESOURCE_LABELS = {
    AUTHENTICATION: 'Autenticação',
    USER: 'Usuários',
    ROLE: 'Perfis',
    USER_IMPORT: 'Importações de usuários',
    SPACE_ALLOCATION_IMPORT: 'Importações de ensalamento',
    EMAIL: 'E-mails',
    AUDIT: 'Auditoria',
    NOTICE: 'Notificações',
    SPACE: 'Espaços',
}

INTERFACE = 'INTERFACE'
SYSTEM = 'SISTEMA'
IMPORTED = 'IMPORTACAO'

ORIGIN_LABELS = {
    INTERFACE: 'Interface',
    SYSTEM: 'Sistema',
    IMPORTED: 'Importação',
}

FIELD_LABELS = {
    'name': 'Nome',
    'email': 'E-mail',
    'role': 'Perfil',
    'code': 'Código',
    'description': 'Descrição',
    'permissions': 'Permissões',
    'superadmin': 'Superadmin',
    'arquivo': 'Arquivo',
    'linhas': 'Linhas',
    'situacao': 'Situação',
    'cadastrados': 'Cadastrados',
    'atualizados': 'Atualizados',
    'sem_alteracao': 'Sem alteração',
    'com_erro': 'Linhas com erro',
    'semestre': 'Semestre',
    'inicio': 'Início do semestre',
    'fim': 'Fim do semestre',
    'inicio_anterior': 'Início anterior',
    'fim_anterior': 'Fim anterior',
    'rota': 'Rota',
    'caminho': 'Caminho',
    'tipo': 'Tipo',
    'referencia': 'Referência',
    'titulo': 'Título',
    'destino': 'Destino',
    'destinatarios': 'Destinatários',
    'outros_nomes': 'Outros nomes',
    'origem': 'Origem',
    'importacao': 'Importação',
    'decidido_por': 'Decidido por',
    'nome_encontrado': 'Nome encontrado',
    'decisao': 'Decisão',
    'espaco': 'Espaço',
    'espacos_cadastrados': 'Espaços cadastrados',
    'outros_nomes_associados': 'Outros nomes associados',
    'espacos_reativados': 'Espaços reativados',
}


def choices(labels):
    """Pares de código e rótulo, na ordem do catálogo, para os filtros da consulta."""
    return list(labels.items())


def label(labels, code):
    return labels.get(code, code)
