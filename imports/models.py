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
                status=Import.Status.WITH_ERRORS if plan.has_errors else Import.Status.VALIDATED,
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


def plan_fields(row_plan):
    return {
        'action': row_plan.action,
        'target': row_plan.target,
        'changes': json.loads(json.dumps(row_plan.changes)),
        'warnings': list(row_plan.warnings),
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

    def summary(self):
        """Totais por ação e linhas com erro, contados a partir das linhas."""
        counts = {'create': 0, 'update': 0, 'unchanged': 0, 'errors': 0}
        for action, errors in self.rows.values_list('action', 'errors'):
            if errors:
                counts['errors'] += 1
            elif action in counts:
                counts[action] += 1
        return counts

    def lock_pending(self):
        current = type(self).objects.select_for_update().get(pk=self.pk)
        if current.status != self.Status.VALIDATED:
            raise ImportNotPending(current.get_status_display())
        return current

    def confirm(self, definition, executor):
        """Reexecuta com o executor atual e aplica só se o plano for idêntico ao gravado (D9).

        Devolve True quando a importação foi concluída. Com o plano diferente, as
        alterações de domínio são desfeitas, o novo plano substitui o anterior e
        devolve False.
        """
        with transaction.atomic():
            current = self.lock_pending()
            rows = list(current.rows.order_by('line_number'))
            savepoint = transaction.savepoint()
            plan = run(definition, [row.as_source() for row in rows], executor)
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
                for row, (_, row_plan) in zip(rows, plan.rows):
                    for name, value in plan_fields(row_plan).items():
                        setattr(row, name, value)
                ImportRow.objects.bulk_update(rows, ['action', 'target', 'changes', 'warnings', 'errors'])
                current.status = self.Status.WITH_ERRORS if plan.has_errors else self.Status.VALIDATED
                current.revalidation_count += 1
                current.file_errors = plan.file_errors_data()
                current.save(update_fields=['status', 'revalidation_count', 'file_errors'])
                concluded = False
        self.refresh_from_db()
        return concluded

    def discard(self, definition, executor):
        with transaction.atomic():
            current = self.lock_pending()
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

    def comparable(self, rows=None):
        rows = rows if rows is not None else self.rows.order_by('line_number')
        return comparable(
            [(row.line_number, row.action, row.target, row.changes, row.warnings, row.errors) for row in rows],
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
