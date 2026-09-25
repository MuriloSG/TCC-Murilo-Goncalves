"""Adoção dos espaços existentes pelo cadastro (D3 da Change manipulacao-dos-espacos).

Antes do cadastro, a importação era o único caminho de criação de espaço. Por isso todo
espaço existente passa a ter a origem `PLANILHA`, ativo, com o próprio nome como nome
atual, e a importação de origem é a importação de ensalamento concluída cuja linha de sala
registrou a criação dele. Nenhum espaço é excluído, renomeado ou unido, nenhuma alocação
muda e nenhum registro de auditoria é criado, porque a auditoria não inventa histórico.
"""

from django.db import migrations


def creating_imports(ImportRow):
    """Importação que criou cada espaço, pela chave gravada na linha de sala na conclusão."""
    origins = {}
    rows = (
        ImportRow.objects.filter(parent__kind='ENSALAMENTO', parent__status='CONCLUIDA', values__Tipo='SALA')
        .exclude(created_object=None)
        .order_by('parent__created_at', 'parent_id')
        .values_list('created_object', 'parent_id')
    )
    for created_object, parent_id in rows:
        origins.setdefault(created_object, parent_id)
    return origins


def adopt_spaces(apps, schema_editor):
    Space = apps.get_model('schedule', 'Space')
    SpaceName = apps.get_model('schedule', 'SpaceName')
    origins = creating_imports(apps.get_model('imports', 'ImportRow'))
    for space in Space.objects.all():
        space.origin = 'PLANILHA'
        space.is_active = True
        space.source_import_id = origins.get(str(space.pk))
        space.save(update_fields=['origin', 'is_active', 'source_import'])
        if not SpaceName.objects.filter(space=space, name__iexact=space.name).exists():
            SpaceName.objects.create(space=space, name=space.name)


def forget_names(apps, schema_editor):
    """Os campos novos saem com a reversão do esquema; aqui só os nomes são apagados."""
    apps.get_model('schedule', 'SpaceName').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0003_space_registry'),
    ]

    operations = [
        migrations.RunPython(adopt_spaces, forget_names),
    ]
