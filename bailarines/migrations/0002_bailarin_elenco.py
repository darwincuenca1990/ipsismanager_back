from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bailarines', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bailarin',
            name='elenco',
            field=models.CharField(
                choices=[
                    ('INFANTIL', 'Infantil'),
                    ('PLANTA', 'Planta'),
                    ('MÁSTER', 'Máster'),
                    ('ASPIRANTE INFANTIL', 'Aspirante infantil'),
                    ('ASPIRANTE PLANTA', 'Aspirante planta'),
                    ('ASPIRANTE MÁSTER', 'Aspirante máster'),
                ],
                default='PLANTA',
                max_length=30,
            ),
            preserve_default=False,
        ),
    ]
