"""Ofertas e docentes das ofertas a partir das alocações existentes (D8 da Change
relacionar-professor-disciplina-turma).

Cada tripla de semestre, disciplina e turma das alocações vira uma oferta, e cada docente
que aparece em alguma versão das alocações dela vira um vínculo. O vínculo é atual quando o
docente está numa alocação sem fim de vigência, e histórico nos demais casos. Nenhuma
alocação muda, e nenhum registro de auditoria é criado. O reverso não faz nada, porque a
migration anterior remove as tabelas.
"""

from django.db import migrations


def backfill(apps, schema_editor):
    Allocation = apps.get_model('schedule', 'Allocation')
    ClassOffering = apps.get_model('schedule', 'ClassOffering')
    TeachingAssignment = apps.get_model('schedule', 'TeachingAssignment')
    teachers = {}
    for semester, subject, group in Allocation.objects.values_list('semester', 'subject', 'class_group').distinct():
        teachers.setdefault((semester, subject, group), {})
    links = Allocation.teachers.through.objects.values_list(
        'allocation__semester', 'allocation__subject', 'allocation__class_group', 'teacher', 'allocation__valid_until',
    )
    for semester, subject, group, teacher, valid_until in links:
        found = teachers[(semester, subject, group)]
        found[teacher] = found.get(teacher, False) or valid_until is None
    for (semester, subject, group), found in teachers.items():
        offering, _ = ClassOffering.objects.get_or_create(semester_id=semester, subject_id=subject, class_group_id=group)
        TeachingAssignment.objects.bulk_create(
            [TeachingAssignment(offering=offering, teacher_id=teacher, is_current=current) for teacher, current in found.items()],
            ignore_conflicts=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0007_class_offering'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
