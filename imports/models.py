import json

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import OperationalError, models, transaction
from django.utils import timezone

from audit import catalog
from audit.models import AuditLog
from imports.definitions import RowError
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


class ImportBusy(ValidationError):
    def __init__(self):
        super().__init__(
            'Esta importação está em processamento e não aceita outra ação até ele terminar. '
            'Confira o resultado no detalhe.',
            code='import_busy',
        )


DIVERGENCE_MESSAGE = 'Os dados mudaram desde a prévia. Confira a nova prévia e confirme de novo.'
PREVIEW_FAILED_MESSAGE = 'A prévia não foi gerada por uma falha do sistema. Envie o arquivo de novo.'
REFRESH_FAILED_MESSAGE = (
    'A atualização da prévia não foi concluída por uma falha do sistema. Nada foi aplicado. Atualize a prévia de novo.'
)
CONFIRMATION_FAILED_MESSAGE = (
    'A confirmação não foi concluída por uma falha do sistema. Nada foi aplicado. Confirme de novo.'
)
INACTIVE_REQUESTER_MESSAGE = 'Quem pediu {operation} está desativado. Nada foi aplicado.'
ERROR_MAX_LENGTH = 500


def describe_error(error):
    return f'{type(error).__name__}: {error}'[:ERROR_MAX_LENGTH]


def retry_delay(attempts):
    """Intervalo da tentativa seguinte, repetindo o último quando há mais tentativas que intervalos."""
    delays = settings.IMPORT_RETRY_DELAYS
    return timedelta(seconds=delays[min(attempts, len(delays)) - 1])


class ImportNotDeletable(ValidationError):
    def __init__(self, status_label):
        super().__init__(
            f'Esta importação está {status_label.lower()} e não pode ser excluída. '
            'Só importações descartadas, com erros ou que falharam podem ser excluídas.',
            code='import_not_deletable',
        )


class ImportManager(models.Manager):
    def request_preview(self, definition, rows, file_name, executor):
        """Grava a importação `RECEBIDA`, com a prévia pendente e as linhas com os valores lidos (D3).

        Os erros da leitura de cada linha são gravados junto, para que a prévia os receba como
        na leitura. Nada é executado na requisição: o worker executa a prévia depois do commit.
        """
        now = timezone.now()
        with transaction.atomic():
            importation = self.create(
                kind=definition.kind,
                status=Import.Status.RECEIVED,
                file_name=file_name[:255],
                created_by=executor,
                operation=Import.Operation.PREVIEW,
                requested_by=executor,
                requested_at=now,
                next_attempt_at=now,
            )
            ImportRow.objects.bulk_create(
                ImportRow(
                    parent=importation, line_number=row.line_number, values=row.values,
                    errors=[{'column': error.column, 'code': error.code, 'message': error.message} for error in row.errors],
                )
                for row in rows
            )
        return importation

    def due(self):
        """Importações com operação pendente cuja próxima tentativa já venceu, na ordem da fila."""
        return self.filter(operation__isnull=False, next_attempt_at__lte=timezone.now()).order_by('next_attempt_at', 'pk')


PLAN_FIELDS = ['action', 'target', 'changes', 'warnings', 'errors', 'pending']
OPERATION_FIELDS = ['operation', 'attempts', 'next_attempt_at', 'last_error', 'outcome', 'outcome_message']


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
        RECEIVED = 'RECEBIDA', 'Recebida'
        VALIDATED = 'VALIDADA', 'Validada'
        PENDING = 'PENDENTE', 'Precisa de decisão'
        WITH_ERRORS = 'COM_ERROS', 'Com erros'
        CONCLUDED = 'CONCLUIDA', 'Concluída'
        DISCARDED = 'DESCARTADA', 'Descartada'
        FAILED = 'FALHOU', 'Falhou'

    class Operation(models.TextChoices):
        PREVIEW = 'PREVIA', 'Prévia'
        REFRESH = 'ATUALIZACAO', 'Atualização da prévia'
        CONFIRMATION = 'CONFIRMACAO', 'Confirmação'

    class Outcome(models.TextChoices):
        DIVERGENCE = 'DIVERGENCIA', 'Divergência'
        REFUSED = 'RECUSADA', 'Recusada'
        REFRESH_FAILED = 'FALHA_ATUALIZACAO', 'Falha na atualização da prévia'
        CONFIRMATION_FAILED = 'FALHA_CONFIRMACAO', 'Falha na confirmação'

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
    operation = models.CharField(
        'operação pendente', max_length=12, choices=Operation.choices, null=True, blank=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', null=True, blank=True,
        verbose_name='operação pedida por',
    )
    requested_at = models.DateTimeField('operação pedida em', null=True, blank=True)
    attempts = models.PositiveSmallIntegerField('tentativas', default=0)
    next_attempt_at = models.DateTimeField('próxima tentativa', null=True, blank=True)
    last_error = models.TextField('último erro', blank=True)
    outcome = models.CharField('resultado da última operação', max_length=20, choices=Outcome.choices, blank=True)
    outcome_message = models.TextField('mensagem do resultado', blank=True)

    objects = ImportManager()

    class Meta:
        verbose_name = 'importação'
        verbose_name_plural = 'importações'
        ordering = ['-created_at', '-pk']
        indexes = [
            models.Index(fields=['kind', '-created_at'], name='import_kind_created_idx'),
            models.Index(
                fields=['next_attempt_at'], condition=models.Q(operation__isnull=False), name='import_pending_operation_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(operation__isnull=True) & ~models.Q(status='RECEBIDA'))
                    | models.Q(operation__isnull=False, operation='PREVIA', status='RECEBIDA')
                    | models.Q(operation__isnull=False, operation='ATUALIZACAO', status__in=['VALIDADA', 'PENDENTE'])
                    | models.Q(operation__isnull=False, operation='CONFIRMACAO', status='VALIDADA')
                ),
                name='import_operation_matches_status',
            ),
        ]

    def __str__(self):
        return f'{self.kind} {self.file_name}'

    @property
    def is_validated(self):
        return self.status == self.Status.VALIDATED

    @property
    def needs_decision(self):
        return self.status == self.Status.PENDING

    @property
    def is_busy(self):
        """Há operação pendente: a importação não aceita outra ação até ela terminar (D5)."""
        return self.operation is not None

    @property
    def has_failed_outcome(self):
        return self.outcome in (self.Outcome.REFRESH_FAILED, self.Outcome.CONFIRMATION_FAILED)

    @property
    def is_stale(self):
        """O pedido passou de `IMPORT_STALE_AFTER`; só alimenta o aviso da tela, sem estado gravado (D13)."""
        if not self.is_busy or self.requested_at is None:
            return False
        return timezone.now() - self.requested_at > timedelta(seconds=settings.IMPORT_STALE_AFTER)

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

    def lock_idle(self):
        """Trava a importação sem esperar e recusa a que tem operação pendente ou está travada (D5).

        A trava ocupada é a do worker executando a operação. A consulta roda num savepoint
        próprio, para que a recusa do banco não invalide a transação de quem chama.
        """
        try:
            with transaction.atomic():
                current = type(self).objects.select_for_update(nowait=True).get(pk=self.pk)
        except OperationalError:
            raise ImportBusy() from None
        if current.is_busy:
            raise ImportBusy()
        return current

    def lock_pending(self, statuses=(Status.VALIDATED,)):
        """Trava a importação livre e confere que ela está numa das situações aceitas pela operação."""
        current = self.lock_idle()
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

    def start(self, operation, executor):
        """Registra a operação pendente, sem mudar a situação, e limpa o resultado anterior."""
        self.operation = operation
        self.requested_by = executor
        self.requested_at = timezone.now()
        self.attempts = 0
        self.next_attempt_at = self.requested_at
        self.last_error = ''
        self.outcome = ''
        self.outcome_message = ''
        self.save(update_fields=['operation', 'requested_by', 'requested_at'] + OPERATION_FIELDS)

    def finish(self, outcome='', message=''):
        """Encerra a operação pendente com o resultado; quem grava é a transição, no mesmo commit."""
        self.operation = None
        self.attempts = 0
        self.next_attempt_at = None
        self.last_error = ''
        self.outcome = outcome
        self.outcome_message = message

    def request_refresh(self, executor):
        """Pede a atualização da prévia de uma importação pendente ou validada (D3).

        A situação não muda, e nenhuma linha é executada na requisição.
        """
        with transaction.atomic():
            current = self.lock_pending((self.Status.VALIDATED, self.Status.PENDING))
            current.start(self.Operation.REFRESH, executor)
        self.refresh_from_db()

    def request_confirmation(self, definition, executor):
        """Pede a confirmação, com a verificação própria da importação já na tela (D3).

        A importação que precisa de decisão e a recusa da verificação não deixam operação
        pendente nem alteram nada. Aceito o pedido, a importação continua `VALIDADA`.
        """
        with transaction.atomic():
            current = self.lock_pending((self.Status.VALIDATED, self.Status.PENDING))
            if current.status == self.Status.PENDING:
                raise ImportNeedsDecision()
            definition.check_confirmation(current, executor)
            current.start(self.Operation.CONFIRMATION, executor)
        self.refresh_from_db()

    def execute_pending(self, definition):
        """Executa a operação pendente, com a pré-condição conferida sob a trava (D3).

        Devolve False quando outra instância tem a trava ou a operação já terminou. Quem
        pediu e foi desativado depois tem a operação recusada sem executar nenhuma linha.
        O resultado de negócio e o fim da operação são gravados no mesmo commit. Um erro
        inesperado desfaz tudo e sobe para o worker.
        """
        with transaction.atomic():
            current = (
                type(self).objects.select_for_update(skip_locked=True)
                .filter(pk=self.pk, operation__isnull=False).first()
            )
            if current is None:
                return False
            executor = current.requested_by
            if not executor.is_active:
                current.refuse(INACTIVE_REQUESTER_MESSAGE.format(operation=current.operation_phrase()))
            elif current.operation == self.Operation.PREVIEW:
                current.run_preview(definition, executor)
            elif current.operation == self.Operation.REFRESH:
                current.run_refresh(definition, executor)
            else:
                current.run_confirmation(definition, executor)
        self.refresh_from_db()
        return True

    def operation_phrase(self):
        return {
            self.Operation.PREVIEW: 'a prévia',
            self.Operation.REFRESH: 'a atualização da prévia',
            self.Operation.CONFIRMATION: 'a confirmação',
        }[self.operation]

    def refuse(self, message):
        """Encerra a operação recusada: a prévia que nunca existiu falha, as demais mantêm a situação."""
        if self.operation == self.Operation.PREVIEW:
            self.status = self.Status.FAILED
            self.finish(message=message)
        else:
            self.finish(self.Outcome.REFUSED, message)
        self.save(update_fields=['status'] + OPERATION_FIELDS)

    def execute_rows(self, definition, executor, with_reader_errors=False):
        rows = list(self.rows.order_by('line_number'))
        return rows, run(definition, [row.as_source(with_reader_errors) for row in rows], executor, self)

    def run_preview(self, definition, executor):
        """Executa e desfaz as linhas gravadas no envio e grava o plano e a situação dada por ele (D7)."""
        with transaction.atomic():
            rows, plan = self.execute_rows(definition, executor, with_reader_errors=True)
            transaction.set_rollback(True)
        self.replace_plan(rows, plan)
        self.finish()
        self.save(update_fields=['status', 'file_errors'] + OPERATION_FIELDS)
        AuditLog.objects.record(
            catalog.CREATE,
            definition.audit_resource,
            resource_id=self.pk,
            metadata={
                'arquivo': self.file_name,
                'situacao': self.status,
                'linhas': len(rows),
            }
            | definition.audit_metadata(rows),
        )

    def run_refresh(self, definition, executor):
        """Refaz a prévia sem aplicar nada (D10 da Change manipulacao-dos-espacos).

        Reexecuta as linhas gravadas num savepoint desfeito, com a importação em curso, e
        substitui o plano e a situação. Não conta como prévia refeita, que conta só as
        divergências da confirmação, e não grava auditoria, como a substituição do plano
        numa divergência.
        """
        with transaction.atomic():
            rows, plan = self.execute_rows(definition, executor)
            transaction.set_rollback(True)
        self.replace_plan(rows, plan)
        self.finish()
        self.save(update_fields=['status', 'file_errors'] + OPERATION_FIELDS)

    def run_confirmation(self, definition, executor):
        """Reexecuta com quem pediu e aplica só se o plano for idêntico ao gravado (D9).

        A verificação própria é repetida antes da reexecução, e a recusa encerra a operação
        sem alterar a situação. Com o plano diferente, as alterações de domínio são
        desfeitas e o novo plano substitui o anterior.
        """
        try:
            definition.check_confirmation(self, executor)
        except ValidationError as error:
            self.finish(self.Outcome.REFUSED, ' '.join(error.messages))
            self.save(update_fields=OPERATION_FIELDS)
            return
        savepoint = transaction.savepoint()
        rows, plan = self.execute_rows(definition, executor)
        if not plan.has_errors and plan.comparable() == self.comparable(rows):
            transaction.savepoint_commit(savepoint)
            for row, (_, row_plan) in zip(rows, plan.rows):
                if row_plan.created is not None:
                    row.created_object = str(row_plan.created)
                    row.save(update_fields=['created_object'])
            self.status = self.Status.CONCLUDED
            self.resolved_by = executor
            self.resolved_at = timezone.now()
            self.finish()
            self.save(update_fields=['status', 'resolved_by', 'resolved_at'] + OPERATION_FIELDS)
            summary = self.summary()
            AuditLog.objects.record(
                catalog.IMPORT,
                definition.audit_resource,
                resource_id=self.pk,
                metadata={
                    'arquivo': self.file_name,
                    'situacao': self.status,
                    'cadastrados': summary['create'],
                    'atualizados': summary['update'],
                    'sem_alteracao': summary['unchanged'],
                    'com_erro': summary['errors'],
                }
                | definition.audit_metadata(rows),
            )
        else:
            transaction.savepoint_rollback(savepoint)
            self.replace_plan(rows, plan)
            self.revalidation_count += 1
            self.finish(self.Outcome.DIVERGENCE, DIVERGENCE_MESSAGE)
            self.save(update_fields=['status', 'revalidation_count', 'file_errors'] + OPERATION_FIELDS)

    def reserve(self):
        """Conta a tentativa e adia a próxima antes de executar, numa transação própria do worker (D4)."""
        self.attempts += 1
        self.next_attempt_at = timezone.now() + retry_delay(self.attempts)
        self.save(update_fields=['attempts', 'next_attempt_at'])

    @property
    def is_exhausted(self):
        return self.attempts >= settings.IMPORT_MAX_ATTEMPTS

    def register_failure(self, error):
        """Guarda o erro da tentativa; a próxima já está agendada desde a reserva (D6)."""
        self.last_error = describe_error(error)
        self.save(update_fields=['last_error'])

    def exhaust(self, definition):
        """Encerra a operação que esgotou as tentativas (D6).

        A prévia que nunca foi gerada leva a importação a `FALHOU`; a atualização e a
        confirmação mantêm a situação e o plano anteriores, com o resultado da falha. Sem
        definição registrada para o tipo, não há módulo de auditoria, e só o log registra.
        """
        if self.operation == self.Operation.PREVIEW:
            self.status = self.Status.FAILED
            self.finish(message=PREVIEW_FAILED_MESSAGE)
        elif self.operation == self.Operation.REFRESH:
            self.finish(self.Outcome.REFRESH_FAILED, REFRESH_FAILED_MESSAGE)
        else:
            self.finish(self.Outcome.CONFIRMATION_FAILED, CONFIRMATION_FAILED_MESSAGE)
        last_error = self.last_error
        self.save(update_fields=['status'] + [name for name in OPERATION_FIELDS if name != 'last_error'])
        if definition is None:
            return
        AuditLog.objects.record(
            catalog.IMPORT_FAIL,
            definition.audit_resource,
            resource_id=self.pk,
            metadata={'arquivo': self.file_name, 'situacao': self.status, 'erro': last_error},
        )

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
        return self.status in (self.Status.DISCARDED, self.Status.WITH_ERRORS, self.Status.FAILED)

    def remove(self, definition, executor):
        """Exclui a importação e as linhas dela, só quando descartada ou com erros.

        Nenhuma delas alterou o domínio, por isso nada além do histórico some. O registro
        de auditoria guarda o arquivo e a situação, já que a importação deixa de existir.
        """
        with transaction.atomic():
            current = self.lock_idle()
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

    def as_source(self, with_reader_errors=False):
        """Linha para a execução; na prévia, com os erros que a leitura gravou no envio."""
        source = SourceRow(self.line_number, self.values)
        if with_reader_errors:
            source.errors = [RowError(error.get('column'), error['code'], error['message']) for error in self.errors]
        return source
