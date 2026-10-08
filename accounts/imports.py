"""Importação de usuários por planilha, com as mesmas operações e validações das telas."""

from django import forms
from django.core.exceptions import ValidationError

from accounts import permissions
from accounts.forms import email_field, username_field
from accounts.models import (
    UNCHANGED,
    Role,
    User,
    normalize_username,
    deferred_administrative_continuity,
    ensure_administrative_continuity,
    lock_active_users,
    validate_institutional_email,
)
from audit import catalog
from imports.definitions import Column, ImportDefinition, RowError, RowPlan, errors_from_validation

INACTIVE_USER = 'inactive_user'


def permission_error(column, action):
    return RowError(column, 'permission_denied', f'Falta a permissão de {action} para esta linha.')


class UserImport(ImportDefinition):
    kind = 'USUARIO'
    audit_resource = catalog.USER_IMPORT
    columns = (Column('E-mail'), Column('Nome'), Column('Perfil'), Column('Nome de usuário', required=False))
    identifier = 'E-mail'
    columns_by_field = {
        'email': 'E-mail', 'name': 'Nome', 'role': 'Perfil', 'username': 'Nome de usuário',
    }
    action_labels = {'create': 'Cadastro', 'update': 'Atualização', 'unchanged': 'Sem alteração'}
    field_labels = {
        'email': 'E-mail', 'name': 'Nome', 'role': 'Perfil', 'username': 'Nome de usuário',
    }
    warning_labels = {INACTIVE_USER: 'Usuário inativo. Os dados serão atualizados e ele continuará inativo.'}

    def normalize_identifier(self, value):
        return User.objects.normalize_email(value)

    def execution(self, importation=None):
        return deferred_administrative_continuity()

    def lock(self, rows, executor):
        """Trava os usuários ativos, pela continuidade administrativa, e os do arquivo."""
        lock_active_users()
        emails = [self.normalize_identifier(row.values['E-mail']) for row in rows]
        list(User.objects.filter(email__in=emails).order_by('pk').select_for_update().values_list('pk', flat=True))

    def clean_values(self, values):
        errors = []
        cleaned = {}
        fields = (
            ('email', email_field()),
            ('name', forms.CharField(max_length=150)),
            ('username', username_field()),
        )
        for field_name, field in fields:
            column = self.columns_by_field[field_name]
            try:
                cleaned[field_name] = field.clean(values[column])
            except ValidationError as error:
                errors += [
                    RowError(column, item.code or 'invalid', message)
                    for item in error.error_list
                    for message in item.messages
                ]
        cleaned['email'] = User.objects.normalize_email(cleaned.get('email', values['E-mail']))
        cleaned['username'] = normalize_username(cleaned.get('username'))
        code = values['Perfil'].strip().upper()
        cleaned['role'] = Role.objects.filter(code=code).first()
        cleaned['role_code'] = code
        if cleaned['role'] is None:
            errors.append(RowError(
                'Perfil', 'unknown_role',
                f'Não existe perfil com o código {code}. Use o código de um perfil cadastrado.',
            ))
        return cleaned, errors

    def execute_row(self, values, executor):
        cleaned, errors = self.clean_values(values)
        user = User.objects.filter(email__iexact=cleaned['email']).first()
        if user is None:
            return self.create(cleaned, errors, executor)
        return self.update(user, cleaned, errors, executor)

    def create(self, cleaned, errors, executor):
        """Planeja o cadastro; o domínio institucional só é exigido aqui, e não na atualização."""
        if not any(error.column == 'E-mail' for error in errors):
            try:
                validate_institutional_email(cleaned['email'])
            except ValidationError as error:
                errors = [RowError('E-mail', error.code, error.messages[0])] + errors
        plan = RowPlan(
            action='create',
            changes={
                'email': [None, cleaned['email']],
                'name': [None, cleaned.get('name')],
                'role': [None, cleaned['role_code']],
                'username': [None, cleaned['username']],
            },
            errors=errors,
        )
        if not executor.has_perm(permissions.USER_CREATE):
            plan.errors.insert(0, permission_error(None, 'cadastrar usuários'))
        if plan.errors:
            return plan
        try:
            user = User.objects.register(
                email=cleaned['email'],
                name=cleaned['name'],
                role=cleaned['role'],
                username=cleaned['username'],
            )
        except ValidationError as error:
            plan.errors = errors_from_validation(error, self.columns_by_field)
            return plan
        plan.created = user.pk
        return plan

    def update(self, user, cleaned, errors, executor):
        """Planeja a atualização; nome de usuário vazio mantém o valor atual."""
        plan = RowPlan(target=user.pk, errors=errors)
        if not user.is_active:
            plan.warnings.append(INACTIVE_USER)
        name, role, username = cleaned.get('name'), cleaned['role'], cleaned['username']
        current_role = user.role
        if name is not None and name != user.name:
            plan.changes['name'] = [user.name, name]
            if not executor.has_perm(permissions.USER_EDIT):
                plan.errors.append(permission_error('Nome', 'editar usuários'))
        if username is not None and username != user.username:
            plan.changes['username'] = [user.username, username]
            if not executor.has_perm(permissions.USER_EDIT):
                plan.errors.append(permission_error('Nome de usuário', 'editar usuários'))
        if role is not None and role != current_role:
            plan.changes['role'] = [current_role.code if current_role else None, role.code]
            if not executor.has_perm(permissions.USER_CHANGE_ROLE):
                plan.errors.append(permission_error('Perfil', 'trocar o perfil de usuários'))
        plan.action = 'update' if plan.changes else 'unchanged'
        if plan.errors:
            return plan
        try:
            if 'name' in plan.changes or 'username' in plan.changes:
                user.update_details(
                    executor,
                    name=name if 'name' in plan.changes else user.name,
                    email=user.email,
                    username=username if 'username' in plan.changes else UNCHANGED,
                )
            if 'role' in plan.changes:
                user.change_role(role)
        except ValidationError as error:
            plan.errors = errors_from_validation(error, self.columns_by_field)
        return plan

    def check_file(self, executor):
        try:
            ensure_administrative_continuity()
        except ValidationError as error:
            return [RowError(None, error.code or 'administrative_continuity', ' '.join(error.messages))]
        return []


def concluded_message(summary, importation=None):
    created, updated = summary['create'], summary['update']
    parts = []
    if created:
        parts.append(f'{created} usuário{"s" if created > 1 else ""} cadastrado{"s" if created > 1 else ""}')
    if updated:
        noun = '' if created else f' usuário{"s" if updated > 1 else ""}'
        parts.append(f'{updated}{noun} atualizado{"s" if updated > 1 else ""}')
    if not parts:
        return 'Importação concluída. Nenhum usuário foi cadastrado ou alterado.'
    message = f'Importação concluída. {" e ".join(parts)}.'
    if created:
        message += ' O link para definir a senha será enviado aos usuários cadastrados.'
    return message
