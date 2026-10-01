"""Vigência sem nenhuma ocorrência: o fim pode ser anterior ao início.

Com esse significado nenhum par de datas da vigência é inválido, e a restrição que exigia
o fim igual ou posterior ao início sai (D2 da Change encerrar-recorrencia-do-ensalamento).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0008_backfill_class_offering'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='allocation',
            name='allocation_validity_valid',
        ),
    ]
