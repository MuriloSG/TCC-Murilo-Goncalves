import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from audit import catalog
from audit.models import AuditLog
from imports.execution import comparable, run
from imports.reader import SourceRow


class ImportNotPending(ValidationError):
    def __init__(self, status_label):
        super().__init__(
            f'Esta importação está {status_label.lower()} e não pode mais ser confirmada nem descartada.',
            code='import_not_pending',
        )


class ImportNeedsDecision(ValidationError):
    def __init__(self):
        super().__init__(
            'Esta importação precisa de decisão e ainda não pode ser confirmada. Tome as decisões pendentes da prévia.',
            code='import_needs_decision',
        )


class ImportNotDeletable(ValidationError):
    def __init__(self, status_label):
        super().__init__(
            f'Esta importação está {status_label.lower()} e não pode ser excluída. '
            'Só importações descartadas ou com erros podem ser excluídas.',
            code='import_not_deletable',
        )


class ImportManager(models.Manager):
    def preview(self, definition, rows, file_name, executor):
        """Executa e desfaz todas as linhas e grava a importação com o plano (D7).

        As alterações de domínio ficam num savepoint que sofre rollback. Só a
        importação e as linhas, com o plano, são gravadas. Um erro inesperado
        desfaz tudo, e a importação não é criada.
        """
        with transaction.atomic():
            with transaction.atomic():
                plan = run(definition, rows, executor)
                transaction.set_rollback(True)
            importation = self.create(
                kind=definition.kind,
                status=Import.status_of(plan),
                file_name=file_name[:255],
                created_by=executor,
                file_errors=plan.file_errors_data(),
            )
            ImportRow.objects.bulk_create(
                ImportRow(parent=importation, line_number=row.line_number, values=row.values, **plan_fields(row_plan))
                for row, row_plan in plan.rows
            )
            AuditLog.objects.record(
                catalog.CREATE,
                definition.audit_resource,
                resource_id=importation.pk,
                metadata={
                    'arquivo': importation.file_name,
                    'situacao': importation.status,
                    'linhas': len(plan.rows),
                }
                | definition.audit_metadata(rows),
            )
        return importation


PLAN_FIELDS = ['action', 'target', 'changes', 'warnings', 'errors', 'pending']


def plan_fields(row_plan):
    return {
        'action': row_plan.action,
        'target': row_plan.target,
        'changes': json.loads(json.dumps(row_plan.changes)),
        'warnings': list(row_plan.warnings),
        'pending': json.loads(json.dumps(row_plan.pending)),
        'errors': [
            {'column': error.column, 'code': error.code, 'message': error.message} for error in row_plan.errors
        ],
    }


class Import(models.Model):
    """Arquivo que chegou à prévia, com a situação e os dados de auditoria (D6).

    O arquivo não é guardado: os valores lidos de cada linha fazem as vezes dele na
    reexecução da confirmação.
    """

    class Status(models.TextChoices):
        VALIDATED = 'VALIDADA', 'Validada'
        PENDING = 'PENDENTE', 'Precisa de decisão'
        WITH_ERRORS = 'COM_ERROS', 'Com erros'
        CONCLUDED = 'CONCLUIDA', 'Concluída'
        DISCARDED = 'DESCARTADA', 'Descartada'

    kind = models.CharField('tipo', max_length=20)
    status = models.CharField('situação', max_length=10, choices=Status.choices)
    file_name = models.CharField('arquivo', max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', verbose_name='enviada por',
    )
    created_at = models.DateTimeField('enviada em', auto_now_add=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', null=True, blank=True,
        verbose_name='confirmada ou descartada por',
    )
    resolved_at = models.DateTimeField('confirmada ou descartada em', null=True, blank=True)
    revalidation_count = models.PositiveIntegerField('prévias refeitas', default=0)
    file_errors = models.JSONField('erros do arquivo', default=list, blank=True)

    objects = ImportManager()

    class Meta:
        verbose_name = 'importação'
        verbose_name_plural = 'importações'
        ordering = ['-created_at', '-pk']
        indexes = [models.Index(fields=['kind', '-created_at'], name='import_kind_created_idx')]

    def __str__(self):
        return f'{self.kind} {self.file_name}'

    @property
    def is_validated(self):
        return self.status == self.Status.VALIDATED

    @property
    def needs_decision(self):
        return self.status == self.Status.PENDING

    @classmethod
    def status_of(cls, plan):
        """Situação dada pelo plano: o erro prevalece sobre a pendência (D10)."""
        if plan.has_errors:
            return cls.Status.WITH_ERRORS
        if plan.has_pending:
            return cls.Status.PENDING
        return cls.Status.VALIDATED

    def summary(self):
        """Totais por ação, linhas com pendência e linhas com erro, contados a partir das linhas."""
        counts = {'create': 0, 'update': 0, 'unchanged': 0, 'pending': 0, 'errors': 0}
        for action, errors, pending in self.rows.values_list('action', 'errors', 'pending'):
            if errors:
                counts['errors'] += 1
            elif pending:
                counts['pending'] += 1
            elif action in counts:
                counts[action] += 1
        return counts

    def lock_pending(self, statuses=(Status.VALIDATED,)):
        """Trava a importação e confere que ela está numa das situações aceitas pela operação."""
        current = type(self).objects.select_for_update().get(pk=self.pk)
        if current.status not in statuses:
            raise ImportNotPending(current.get_status_display())
        return current

    def replace_plan(self, rows, plan):
        """Grava o novo plano das linhas, os erros do arquivo e a situação dada pelo plano."""
        for row, (_, row_plan) in zip(rows, plan.rows):
            for name, value in plan_fields(row_plan).items():
                setattr(row, name, value)
        ImportRow.objects.bulk_update(rows, PLAN_FIELDS)
        self.status = self.status_of(plan)
        self.file_errors = plan.file_errors_data()

    def refresh(self, definition, executor):
        """Refaz a prévia de uma importação pendente ou validada, sem aplicar nada (D10).

        Reexecuta as linhas gravadas num savepoint desfeito, com a importação em curso, e
        substitui o plano e a situação. Não conta como prévia refeita, que conta só as
        divergências da confirmação, e não grava auditoria, como a substituição do plano
        numa divergência. Um erro inesperado desfaz tudo.
        """
        with transaction.atomic():
            current = self.lock_pending((self.Status.VALIDATED, self.Status.PENDING))
            rows = list(current.rows.order_by('line_number'))
            with transaction.atomic():
                plan = run(definition, [row.as_source() for row in rows], executor, current)
                transaction.set_rollback(True)
            current.replace_plan(rows, plan)
            current.save(update_fields=['status', 'file_errors'])
        self.refresh_from_db()
        return self.status

    def confirm(self, definition, executor):
        """Reexecuta com o executor atual e aplica só se o plano for idêntico ao gravado (D9).

        Devolve True quando a importação foi concluída. Com o plano diferente, as
        alterações de domínio são desfeitas, o novo plano substitui o anterior e
        devolve False. A importação que precisa de decisão é recusada, e a verificação
        própria da importação específica roda antes da reexecução, sem alterar nada
        quando recusa (D10 da Change manipulacao-dos-espacos).
        """
        with transaction.atomic():
            current = self.lock_pending((self.Status.VALIDATED, self.Status.PENDING))
            if current.status == self.Status.PENDING:
                raise ImportNeedsDecision()
            definition.check_confirmation(current, executor)
            rows = list(current.rows.order_by('line_number'))
            savepoint = transaction.savepoint()
            plan = run(definition, [row.as_source() for row in rows], executor, current)
            if not plan.has_errors and plan.comparable() == current.comparable(rows):
                transaction.savepoint_commit(savepoint)
                for row, (_, row_plan) in zip(rows, plan.rows):
                    if row_plan.created is not None:
                        row.created_object = str(row_plan.created)
                        row.save(update_fields=['created_object'])
                current.status = self.Status.CONCLUDED
                current.resolved_by = executor
                current.resolved_at = timezone.now()
                current.save(update_fields=['status', 'resolved_by', 'resolved_at'])
                summary = current.summary()
                AuditLog.objects.record(
                    catalog.IMPORT,
                    definition.audit_resource,
                    resource_id=current.pk,
                    metadata={
                        'arquivo': current.file_name,
                        'situacao': current.status,
                        'cadastrados': summary['create'],
                        'atualizados': summary['update'],
                        'sem_alteracao': summary['unchanged'],
                        'com_erro': summary['errors'],
                    }
                    | definition.audit_metadata(rows),
                )
                concluded = True
            else:
                transaction.savepoint_rollback(savepoint)
                current.replace_plan(rows, plan)
                current.revalidation_count += 1
                current.save(update_fields=['status', 'revalidation_count', 'file_errors'])
                concluded = False
        self.refresh_from_db()
        return concluded

    def discard(self, definition, executor):
        with transaction.atomic():
            current = self.lock_pending((self.Status.VALIDATED, self.Status.PENDING))
            current.status = self.Status.DISCARDED
            current.resolved_by = executor
            current.resolved_at = timezone.now()
            current.save(update_fields=['status', 'resolved_by', 'resolved_at'])
            AuditLog.objects.record(
                catalog.DISCARD,
                definition.audit_resource,
                resource_id=current.pk,
                metadata={'arquivo': current.file_name} | definition.audit_metadata(current.rows.all()),
            )
        self.refresh_from_db()

    @property
    def is_deletable(self):
        return self.status in (self.Status.DISCARDED, self.Status.WITH_ERRORS)

    def remove(self, definition, executor):
        """Exclui a importação e as linhas dela, só quando descartada ou com erros.

        Nenhuma delas alterou o domínio, por isso nada além do histórico some. O registro
        de auditoria guarda o arquivo e a situação, já que a importação deixa de existir.
        """
        with transaction.atomic():
            current = type(self).objects.select_for_update().get(pk=self.pk)
            if not current.is_deletable:
                raise ImportNotDeletable(current.get_status_display())
            AuditLog.objects.record(
                catalog.DELETE,
                definition.audit_resource,
                resource_id=current.pk,
                metadata={'arquivo': current.file_name, 'situacao': current.status}
                | definition.audit_metadata(current.rows.all()),
            )
            current.delete()

    def comparable(self, rows=None):
        rows = rows if rows is not None else self.rows.order_by('line_number')
        return comparable(
            [
                (row.line_number, row.action, row.target, row.changes, row.warnings, row.errors, row.pending)
                for row in rows
            ],
            self.file_errors,
        )


class ImportRow(models.Model):
    class Action(models.TextChoices):
        CREATE = 'create', 'Cadastro'
        UPDATE = 'update', 'Atualização'
        UNCHANGED = 'unchanged', 'Sem alteração'

    parent = models.ForeignKey(Import, on_delete=models.CASCADE, related_name='rows', verbose_name='importação')
    line_number = models.PositiveIntegerField('linha')
    values = models.JSONField('valores lidos')
    action = models.CharField('ação', max_length=10, choices=Action.choices, null=True, blank=True)
    target = models.CharField('alvo', max_length=64, null=True, blank=True)
    changes = models.JSONField('mudanças', default=dict, blank=True)
    warnings = models.JSONField('avisos', default=list, blank=True)
    errors = models.JSONField('erros', default=list, blank=True)
    pending = models.JSONField('pendências', default=list, blank=True)
    created_object = models.CharField('registro criado', max_length=64, null=True, blank=True)

    class Meta:
        verbose_name = 'linha da importação'
        verbose_name_plural = 'linhas da importação'
        ordering = ['line_number']
        constraints = [
            models.UniqueConstraint(fields=['parent', 'line_number'], name='import_row_line_unique'),
        ]

    def __str__(self):
        return f'{self.parent} linha {self.line_number}'

    def as_source(self):
        return SourceRow(self.line_number, self.values)
