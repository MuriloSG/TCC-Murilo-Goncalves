"""Relatório de solicitações de agendamento: a demanda do semestre e como ela foi atendida.

Calculado a cada requisição e nunca gravado (Change gerar-relatorio-de-solicitacoes). Uma
solicitação pertence ao semestre pela data de uso dentro do período dele (D1). Uma consulta
traz as solicitações do recorte, e as contagens, a mediana e os rankings saem em Python (D9).
"""

import math
from dataclasses import dataclass, field
from datetime import timedelta
from statistics import median

from django.utils import timezone

from bookings.models import BookingRequest
from panel.indicators import step, waiting_text

Status = BookingRequest.Status
DECIDED = (Status.APPROVED, Status.REJECTED, Status.DECLINED)
STATUS_ORDER = (Status.PENDING, Status.SUGGESTED, Status.APPROVED, Status.REJECTED, Status.DECLINED)
RANKING_SIZE = 10
RECENT_SIZE = 10
SPLIT_LABEL_WEEKS = 12
AXIS_STEPS = (1, 2, 5)
AXIS_INTERVALS = 4
AXIS_MIN_TOP = 4

STATUS_COUNTS = {
    Status.PENDING: ('pendente', 'pendentes'),
    Status.SUGGESTED: ('com alternativa sugerida', 'com alternativa sugerida'),
    Status.APPROVED: ('aprovada', 'aprovadas'),
    Status.REJECTED: ('rejeitada', 'rejeitadas'),
    Status.DECLINED: ('com alternativa recusada', 'com alternativa recusada'),
}


def plural(count, singular, many):
    return f'{count} {singular if count == 1 else many}'


def listing(parts):
    """Partes unidas por vírgula, com "e" antes da última."""
    if len(parts) <= 1:
        return ''.join(parts)
    return f"{', '.join(parts[:-1])} e {parts[-1]}"


def duration_text(delta):
    """Tempo corrido por extenso: "40 minutos", "3 horas", "1 dia e 4 horas"."""
    total_minutes = int(delta.total_seconds() // 60)
    if total_minutes < 60:
        return plural(max(total_minutes, 1), 'minuto', 'minutos')
    hours = total_minutes // 60
    if hours < 24:
        return plural(hours, 'hora', 'horas')
    days, rest = divmod(hours, 24)
    text = plural(days, 'dia', 'dias')
    return f"{text} e {plural(rest, 'hora', 'horas')}" if rest else text


def percent(part, whole):
    return round(part * 100 / whole) if whole else 0


@dataclass
class Filters:
    semester: object
    stage: str = ''
    course: object = None
    spaces: list = field(default_factory=list)


@dataclass
class Week:
    """Uma semana do período, de segunda a domingo, com as contagens por situação (D3)."""

    number: int
    start: object
    end: object
    counts: dict = field(default_factory=dict)
    height: int = 0
    show_label: bool = True
    left_half: bool = True
    is_current: bool = False
    is_peak: bool = False

    @property
    def total(self):
        return sum(self.counts.values())

    @property
    def label(self):
        return f'S{self.number}'

    @property
    def title(self):
        current = ' (atual)' if self.is_current else ''
        return f'Semana {self.number}{current}, de {self.start:%d/%m/%Y} a {self.end:%d/%m/%Y}'

    @property
    def detail(self):
        """Total e divisão por situação, para a dica e o rótulo acessível da coluna."""
        total = plural(self.total, 'solicitação', 'solicitações')
        parts = [plural(self.counts[status], *STATUS_COUNTS[status]) for status in STATUS_ORDER if self.counts.get(status)]
        return f'{total}: {listing(parts)}.' if parts else f'{total}.'

    @property
    def hint_id(self):
        return f'dica-semana-{self.number}'

    @property
    def hint_align(self):
        """A dica abre no topo do gráfico, no lado oposto ao da coluna, para não cobri-la."""
        return 'end' if self.left_half else ''


@dataclass
class StatusRow:
    """Uma situação com a contagem, o percentual e a largura da barra sobre o total."""

    status: str
    count: int
    percent: int
    width: int = 0

    @property
    def label(self):
        return Status(self.status).label


@dataclass
class SpaceDemand:
    """Solicitações de um espaço no período, com a largura da barra do ranking (D6)."""

    space: object
    total: int = 0
    approved: int = 0
    rejected: int = 0
    width: int = 0

    @property
    def rejection_percent(self):
        return percent(self.rejected, self.total)


@dataclass
class Report:
    semester: object
    total: int = 0
    on_behalf: int = 0
    decided: int = 0
    approved: int = 0
    pending: int = 0
    oldest_pending: str = ''
    decision_time: str = ''
    statuses: list = field(default_factory=list)
    suggested: int = 0
    suggestion_accepted: int = 0
    suggestion_declined: int = 0
    suggestion_rejected: int = 0
    suggestion_awaiting: int = 0
    weeks: list = field(default_factory=list)
    axis: list = field(default_factory=list)
    peak: object = None
    spaces: list = field(default_factory=list)
    rejections: list = field(default_factory=list)

    @property
    def approval_percent(self):
        return percent(self.approved, self.decided)

    @property
    def suggested_percent(self):
        return percent(self.suggested, self.total)

    @property
    def week_count(self):
        return len(self.weeks)

    @property
    def week_average(self):
        return self.total / len(self.weeks) if self.weeks else 0


def axis_ticks(highest):
    """Marcas do eixo do gráfico, do topo ao zero, em passos de 1, 2 ou 5 vezes uma potência
    de dez, com no máximo quatro intervalos.

    O topo nunca fica abaixo de 4, para que uma semana com 2 solicitações não pareça cheia
    (D12).
    """
    top = max(highest, AXIS_MIN_TOP)
    magnitude = 1
    while True:
        for base in AXIS_STEPS:
            size = base * magnitude
            intervals = math.ceil(top / size)
            if intervals <= AXIS_INTERVALS:
                return [size * index for index in range(intervals, -1, -1)]
        magnitude *= 10


def semester_weeks(semester, today):
    """Semanas de segunda a domingo que cobrem o período; a Semana 1 contém o início (D3)."""
    first = semester.start_date - timedelta(days=semester.start_date.weekday())
    weeks = []
    start = first
    while start <= semester.end_date:
        weeks.append(Week(number=len(weeks) + 1, start=start, end=start + timedelta(days=6)))
        start += timedelta(days=7)
    for week in weeks:
        week.show_label = len(weeks) <= SPLIT_LABEL_WEEKS or week.number % 2 == 1
        week.left_half = week.number <= len(weeks) / 2
        week.is_current = week.start <= today <= week.end
    return weeks, first


def chosen_requests(filters):
    """Solicitações com data de uso no período do semestre, com os filtros de etapa, curso e
    espaços. Com etapa ou curso, as solicitações sem vínculo acadêmico ficam de fora (D8)."""
    semester = filters.semester
    requests = BookingRequest.objects.filter(date__range=(semester.start_date, semester.end_date))
    if filters.course is not None:
        requests = requests.filter(teaching_assignment__offering__class_group__course=filters.course)
    elif filters.stage:
        requests = requests.filter(teaching_assignment__offering__class_group__course__stage=filters.stage)
    if filters.spaces:
        requests = requests.filter(space__in=filters.spaces)
    return requests.select_related('space', 'requested_by')


def build(filters, today=None):
    """O relatório do semestre filtrado, ou None quando o semestre não tem período (D1)."""
    semester = filters.semester
    if semester is None or not semester.has_period:
        return None
    today = today or timezone.localdate()
    requests = list(chosen_requests(filters))
    report = Report(semester=semester, total=len(requests))
    weeks, first = semester_weeks(semester, today)
    report.weeks = weeks
    counts = {status: 0 for status in STATUS_ORDER}
    durations = []
    demand = {}
    oldest = None
    for request in requests:
        counts[request.status] += 1
        week = weeks[(request.date - first).days // 7]
        week.counts[request.status] = week.counts.get(request.status, 0) + 1
        if request.created_by_id:
            report.on_behalf += 1
        if request.decided_at:
            durations.append(request.decided_at - request.created_at)
        if request.is_open and (oldest is None or request.created_at < oldest):
            oldest = request.created_at
        if request.has_suggestion:
            report.suggested += 1
            report.suggestion_accepted += request.status == Status.APPROVED
            report.suggestion_declined += request.status == Status.DECLINED
            report.suggestion_rejected += request.status == Status.REJECTED
            report.suggestion_awaiting += request.status == Status.SUGGESTED
        space = demand.setdefault(request.space_id, SpaceDemand(space=request.space))
        space.total += 1
        space.approved += request.status == Status.APPROVED
        space.rejected += request.status == Status.REJECTED
    report.decided = sum(counts[status] for status in DECIDED)
    report.approved = counts[Status.APPROVED]
    report.pending = counts[Status.PENDING] + counts[Status.SUGGESTED]
    report.oldest_pending = waiting_text(oldest, today) if oldest else ''
    report.decision_time = duration_text(median(durations)) if durations else ''
    report.statuses = [
        StatusRow(status, counts[status], percent(counts[status], report.total), step(counts[status], report.total))
        for status in STATUS_ORDER
    ]
    highest = max((week.total for week in weeks), default=0)
    report.axis = axis_ticks(highest)
    for week in weeks:
        week.height = step(week.total, report.axis[0])
    if highest:
        peak = next(week for week in weeks if week.total == highest)
        peak.is_peak = True
        report.peak = peak
    ranking = sorted(demand.values(), key=lambda item: (-item.total, item.space.name))[:RANKING_SIZE]
    for item in ranking:
        item.width = step(item.total, ranking[0].total)
    report.spaces = ranking
    rejected = [request for request in requests if request.status == Status.REJECTED]
    report.rejections = sorted(rejected, key=lambda request: (request.decided_at, request.pk), reverse=True)[:RECENT_SIZE]
    return report
