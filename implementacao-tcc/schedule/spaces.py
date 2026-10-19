"""Classificação dos nomes de espaço pelas linhas, cadastro e decisões; nome só das células nunca é proposto como novo."""

from dataclasses import dataclass, field

from django.db.models import prefetch_related_objects

from accounts import permissions
from schedule.activities import ACTIVITY_COLUMN, Catalog, resolve
from schedule.models import Space, SpaceDecision, SpaceName, SpaceOrigin
from schedule.sheets import (
    ACTIVITY_KIND,
    SPACE_KIND,
    TEACHER_KIND,
    parse_weekday,
    split_header,
    strip_parentheses,
    text,
)
from schedule.similarity import similar_names

KIND_COLUMN = 'Tipo'
NAME_COLUMN = 'Nome'
DAY_COLUMN = 'Dia'
GROUP_COLUMN = 'Turma'
COURSE_COLUMN = 'Curso'

RECOGNIZED = 'reconhecido'
CREATE = 'cadastrar'
ASSOCIATE = 'associar'
REACTIVATE = 'reativar'
PENDING = 'precisa_de_decisao'

INACTIVE = 'inativo'
SIMILAR = 'parecido'
CELLS_ONLY = 'so_nas_aulas'


def key_of(name):
    return name.casefold()


def list_name(values):
    """Nome de uma linha da lista de salas, com os parênteses retirados, como na execução."""
    return strip_parentheses(text(values.get(NAME_COLUMN)))


@dataclass
class Usage:
    """Uso agregado de um nome encontrado: aulas, turmas e dias da semana."""

    lessons: int = 0
    groups: set = field(default_factory=set)
    weekdays: set = field(default_factory=set)


@dataclass
class Candidate:
    """Espaço parecido com um nome encontrado: do cadastro ou outro nome da mesma importação."""

    name: str
    space: Space | None = None
    found_key: str | None = None

    @property
    def is_inactive(self):
        return self.space is not None and not self.space.is_active


@dataclass
class FoundName:
    """Nome de espaço encontrado na planilha, com a classificação e o que ele causará."""

    key: str
    name: str
    from_list: bool
    usage: Usage = field(default_factory=Usage)
    space: Space | None = None
    candidates: list = field(default_factory=list)
    decision: SpaceDecision | None = None
    outcome: str = PENDING
    reason: str | None = None
    target: Space | None = None
    target_key: str | None = None

    @property
    def identifies_inactive(self):
        return self.space is not None and not self.space.is_active

    @property
    def is_current_name_of_inactive(self):
        return self.identifies_inactive and key_of(self.space.name) == self.key

    @property
    def moves_from(self):
        """Espaço inativo que perde este nome, quando ele era outro nome dele e vai para outro espaço."""
        if not self.identifies_inactive or self.is_current_name_of_inactive:
            return None
        if self.outcome == CREATE or (self.outcome == ASSOCIATE and self.target != self.space):
            return self.space
        return None

    @property
    def reactivates(self):
        """Espaço que a confirmação reativa por causa deste nome."""
        if self.outcome == REACTIVATE:
            return self.space
        if self.outcome == ASSOCIATE and self.target is not None and not self.target.is_active:
            return self.target
        return None

    @property
    def decider(self):
        return self.decision.decided_by if self.decision is not None else None


@dataclass
class Resolution:
    """Resultado da classificação de uma importação."""

    found: dict = field(default_factory=dict)
    catalog: Catalog = None

    def with_outcome(self, outcome):
        return [entry for entry in self.found.values() if entry.outcome == outcome]

    @property
    def recognized(self):
        return self.with_outcome(RECOGNIZED)

    @property
    def to_create(self):
        return self.with_outcome(CREATE)

    @property
    def proposed(self):
        return [entry for entry in self.to_create if entry.decision is None]

    @property
    def to_associate(self):
        return self.with_outcome(ASSOCIATE)

    @property
    def to_reactivate(self):
        return [entry for entry in self.found.values() if entry.reactivates is not None]

    @property
    def pending(self):
        return self.with_outcome(PENDING)

    def aliases_of(self, key):
        """Nomes encontrados que a confirmação guarda como outros nomes do espaço criado para `key`."""
        return [entry.name for entry in self.to_associate if entry.target_key == key]

    def changes_registry(self):
        return bool(self.to_create or self.to_associate or self.to_reactivate)

    def required_permissions(self):
        """Permissões de espaço exigidas de quem confirma, pelo que a confirmação alterará."""
        required = set()
        for entry in self.found.values():
            required |= effect_permissions(entry.outcome, entry.target, entry.target_key, entry.moves_from)
            if entry.reactivates is not None:
                required.add(permissions.SPACE_CHANGE_STATUS)
        return required


def effect_permissions(outcome, target=None, target_key=None, moves_from=None):
    """Permissões de espaço de uma alteração do cadastro, sem a reativação."""
    required = set()
    if outcome == CREATE or (outcome == ASSOCIATE and target_key is not None):
        required.add(permissions.SPACE_CREATE)
    if outcome == ASSOCIATE and target is not None:
        required.add(permissions.SPACE_EDIT)
    if moves_from is not None:
        required.add(permissions.SPACE_EDIT)
    return required


def registry():
    """Nomes do cadastro com os outros nomes numa só consulta."""
    items = list(SpaceName.objects.select_related('space'))
    prefetch_related_objects([item.space for item in items], 'names')
    return {key_of(item.name): (item.name, item.space) for item in items}


def read_found(values_list, registry_names):
    """Nomes encontrados com a origem e o uso; os da lista sem aula entram depois, com uso zerado."""
    listed = {}
    teachers = []
    for values in values_list:
        kind = values.get(KIND_COLUMN)
        if kind == SPACE_KIND:
            name = list_name(values)
            if name:
                listed.setdefault(key_of(name), name)
        elif kind == TEACHER_KIND:
            teachers.append(text(values.get(NAME_COLUMN)))
    catalog = Catalog.build(teachers, [*listed.values(), *(name for name, _ in registry_names.values())])
    found = {}
    for values in values_list:
        if values.get(KIND_COLUMN) != ACTIVITY_KIND:
            continue
        activity = resolve(text(values.get(ACTIVITY_COLUMN)), catalog)
        name = activity.space_name or activity.cell_space_name
        if not name:
            continue
        key = key_of(name)
        entry = found.get(key)
        if entry is None:
            entry = found[key] = FoundName(key=key, name=listed.get(key, name), from_list=key in listed)
        label, short_name = split_header(values.get(GROUP_COLUMN))
        entry.usage.lessons += 1
        entry.usage.groups.add((text(values.get(COURSE_COLUMN)) or short_name, label))
        weekday = parse_weekday(values.get(DAY_COLUMN))
        if weekday:
            entry.usage.weekdays.add(weekday)
    for key, name in listed.items():
        known = registry_names.get(key)
        if key not in found and (known is None or known[1].is_active):
            found[key] = FoundName(key=key, name=name, from_list=True)
    return found, catalog


def candidates_of(entry, found, registry_names):
    """Parecidos no cadastro e nos demais nomes; nome da lista sem aula não torna ambíguo um usado."""
    known_spaces = {}
    for name, space in registry_names.values():
        known_spaces.setdefault(name, space)
    others = [
        other for other in found.values()
        if other.key != entry.key
        and (other.from_list or not entry.from_list)
        and (other.usage.lessons or not entry.usage.lessons)
    ]
    result, seen = [], set()
    for name in similar_names(entry.name, list(known_spaces)):
        space = known_spaces[name]
        if space.pk in seen or (entry.space is not None and space.pk == entry.space.pk):
            continue
        seen.add(space.pk)
        result.append(Candidate(name=space.name, space=space))
    by_name = {other.name: other for other in others if other.key not in registry_names}
    for name in similar_names(entry.name, list(by_name)):
        result.append(Candidate(name=name, found_key=by_name[name].key))
    return result


def default_outcome(entry):
    """Classificação do nome sem decisão: novo proposto ou precisa de decisão."""
    if entry.identifies_inactive:
        return PENDING, INACTIVE
    if not entry.from_list:
        return PENDING, SIMILAR if entry.candidates else CELLS_ONLY
    if entry.candidates:
        return PENDING, SIMILAR
    return CREATE, None


def apply_decision(entry, decision):
    """Aplica a decisão gravada quando ela é válida para o nome; devolve se ela foi aplicada."""
    if decision.kind == SpaceDecision.Kind.REACTIVATE:
        if not entry.identifies_inactive:
            return False
        entry.outcome = REACTIVATE
    elif decision.kind == SpaceDecision.Kind.NEW:
        if entry.is_current_name_of_inactive:
            return False
        entry.outcome = CREATE
    elif decision.space_id is not None:
        if entry.is_current_name_of_inactive and decision.space_id != entry.space.pk:
            return False
        if entry.space is not None and decision.space_id == entry.space.pk:
            entry.outcome = REACTIVATE
        else:
            entry.outcome, entry.target = ASSOCIATE, decision.space
    elif decision.target_name:
        if entry.is_current_name_of_inactive or key_of(decision.target_name) == entry.key:
            return False
        entry.outcome, entry.target_key = ASSOCIATE, key_of(decision.target_name)
    else:
        return False
    entry.decision = decision
    return True


def decisions_of(importation):
    if importation is None or importation.pk is None:
        return {}
    decisions = SpaceDecision.objects.filter(importation=importation).select_related('space', 'decided_by')
    return {key_of(decision.found_name): decision for decision in decisions}


def classify(values_list, importation=None):
    """Classifica os nomes de espaço das linhas de uma importação."""
    registry_names = registry()
    found, catalog = read_found(values_list, registry_names)
    decisions = decisions_of(importation)
    for entry in found.values():
        known = registry_names.get(entry.key)
        entry.space = known[1] if known else None
        entry.candidates = candidates_of(entry, found, registry_names)
    for entry in found.values():
        if entry.space is not None and entry.space.is_active:
            entry.outcome = RECOGNIZED
            continue
        decision = decisions.get(entry.key)
        if decision is None or not apply_decision(entry, decision):
            entry.outcome, entry.reason = default_outcome(entry)
    for entry in found.values():
        if entry.outcome == ASSOCIATE and entry.target_key is not None:
            target = found.get(entry.target_key)
            if target is None or target.outcome != CREATE:
                entry.decision, entry.target_key = None, None
                entry.outcome, entry.reason = default_outcome(entry)
    return Resolution(found=found, catalog=catalog)


def classify_import(importation):
    """Classificação a partir das linhas gravadas de uma importação."""
    values_list = list(importation.rows.order_by('line_number').values_list('values', flat=True))
    return classify(values_list, importation)


@dataclass
class Applied:
    """O que a execução aplicou ao cadastro; `altered` são os espaços existentes alterados."""

    spaces: dict = field(default_factory=dict)
    created: set = field(default_factory=set)
    previous_names: dict = field(default_factory=dict)
    reactivated: set = field(default_factory=set)
    altered: set = field(default_factory=set)


def metadata_of(entry, importation):
    metadata = {}
    if importation is not None and importation.pk is not None:
        metadata['importacao'] = importation.pk
    if entry is not None and entry.decider is not None:
        metadata['decidido_por'] = entry.decider.email
    return metadata or None


def apply(resolution, importation=None):
    """Aplica a classificação ao cadastro numa ordem que libera cada grafia antes de reusá-la."""
    applied = Applied()
    entries = list(resolution.found.values())
    for entry in entries:
        for space in {entry.space, entry.target} - {None}:
            applied.previous_names.setdefault(space.pk, (space.other_names, space.is_active))
    for entry in entries:
        if entry.moves_from is not None:
            entry.moves_from.remove_name(entry.name, metadata=metadata_of(entry, importation))
            applied.altered.add(entry.moves_from.pk)
    for entry in entries:
        space = entry.reactivates
        if space is not None and space.pk not in applied.reactivated:
            space.reactivate(metadata=metadata_of(entry, importation))
            applied.reactivated.add(space.pk)
            applied.altered.add(space.pk)
    source = importation if importation is not None and importation.pk is not None else None
    for entry in resolution.to_create:
        space = Space.objects.register(
            entry.name,
            other_names=resolution.aliases_of(entry.key),
            origin=SpaceOrigin.SPREADSHEET,
            source_import=source,
            metadata=metadata_of(entry, importation),
        )
        applied.spaces[entry.key] = space
        applied.created.add(space.pk)
    for entry in resolution.to_associate:
        if entry.target_key is not None:
            applied.spaces[entry.key] = applied.spaces[entry.target_key]
            continue
        entry.target.add_name(entry.name, metadata=metadata_of(entry, importation))
        applied.altered.add(entry.target.pk)
        applied.spaces[entry.key] = entry.target
    for entry in entries:
        if entry.outcome in (RECOGNIZED, REACTIVATE):
            applied.spaces[entry.key] = entry.space
    return applied


def options_of(entry):
    """Decisões que o nome aceita: novo, mesmo que um espaço ou outro nome, e reativar."""
    if entry.outcome == RECOGNIZED:
        return set()
    if entry.is_current_name_of_inactive:
        return {SpaceDecision.Kind.REACTIVATE}
    options = {SpaceDecision.Kind.NEW, SpaceDecision.Kind.SAME}
    if entry.identifies_inactive:
        options.add(SpaceDecision.Kind.REACTIVATE)
    return options


def decision_permissions(entry, kind, space=None, target_name=''):
    """Permissões de espaço exigidas para tomar uma decisão sobre o nome."""
    moves = entry.identifies_inactive and not entry.is_current_name_of_inactive
    if kind == SpaceDecision.Kind.REACTIVATE:
        return {permissions.SPACE_CHANGE_STATUS}
    if kind == SpaceDecision.Kind.NEW:
        return {permissions.SPACE_CREATE} | ({permissions.SPACE_EDIT} if moves else set())
    if space is not None and entry.space is not None and space.pk == entry.space.pk:
        return {permissions.SPACE_CHANGE_STATUS}
    if space is not None:
        required = {permissions.SPACE_EDIT}
        if not space.is_active:
            required.add(permissions.SPACE_CHANGE_STATUS)
        return required
    return {permissions.SPACE_CREATE} | ({permissions.SPACE_EDIT} if moves else set())
