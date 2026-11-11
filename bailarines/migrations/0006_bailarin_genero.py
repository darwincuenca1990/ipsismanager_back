from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bailarines', '0005_bailarin_fotografia_drive_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='bailarin',
            name='genero',
            field=models.CharField(
                blank=True,
                choices=[('MASCULINO', 'Masculino'), ('FEMENINO', 'Femenino')],
                max_length=9,
                null=True,
            ),
        ),
    ]
