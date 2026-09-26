"""Extensão `btree_gist`, exigida pela restrição de exclusão dos agendamentos (D3).

Ela permite combinar a igualdade do espaço com a sobreposição do intervalo no mesmo
índice GiST.
"""

from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations


class Migration(migrations.Migration):

    operations = [
        BtreeGistExtension(),
    ]
