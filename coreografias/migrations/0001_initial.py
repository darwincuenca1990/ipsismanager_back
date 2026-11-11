from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Coreografia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=150)),
                ('region', models.CharField(max_length=150)),
                ('descripcion', models.TextField()),
                ('url_video', models.URLField(max_length=500)),
            ],
            options={
                'verbose_name': 'Coreografía',
                'verbose_name_plural': 'Coreografías',
                'db_table': 'coreografias_coreografia',
                'ordering': ['nombre', 'id'],
            },
        ),
    ]
