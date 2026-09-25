import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('imports', '0002_import_pending'),
        ('schedule', '0002_semester_period'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='space',
            name='origin',
            field=models.CharField(choices=[('MANUAL', 'Manual'), ('PLANILHA', 'Planilha')], default='PLANILHA', max_length=8, verbose_name='origem'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='space',
            name='source_import',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='imports.import', verbose_name='importação de origem'),
        ),
        migrations.AddField(
            model_name='space',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='ativo'),
        ),
        migrations.CreateModel(
            name='SpaceName',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='nome')),
                ('space', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='names', to='schedule.space', verbose_name='espaço')),
            ],
            options={
                'verbose_name': 'nome do espaço',
                'verbose_name_plural': 'nomes dos espaços',
                'ordering': ['name'],
                'constraints': [models.UniqueConstraint(django.db.models.functions.text.Lower('name'), name='space_alias_unique_ci', violation_error_message='Já existe um espaço com este nome.')],
            },
        ),
        migrations.CreateModel(
            name='SpaceDecision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('found_name', models.CharField(max_length=200, verbose_name='nome encontrado')),
                ('kind', models.CharField(choices=[('NOVO', 'É um espaço novo'), ('ASSOCIAR', 'É o mesmo que'), ('REATIVAR', 'Reativar')], max_length=8, verbose_name='decisão')),
                ('target_name', models.CharField(blank=True, default='', max_length=200, verbose_name='nome de destino')),
                ('decided_at', models.DateTimeField(auto_now=True, verbose_name='decidida em')),
                ('decided_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='decidida por')),
                ('importation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='space_decisions', to='imports.import', verbose_name='importação')),
                ('space', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='decisions', to='schedule.space', verbose_name='espaço')),
            ],
            options={
                'verbose_name': 'decisão de espaço',
                'verbose_name_plural': 'decisões de espaço',
                'ordering': ['found_name'],
                'constraints': [models.UniqueConstraint(models.F('importation'), django.db.models.functions.text.Lower('found_name'), name='space_decision_unique_ci')],
            },
        ),
    ]
