# Generated by Django 4.2.11 on 2024-05-01 07:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maps', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='facility',
            name='used_seats',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
