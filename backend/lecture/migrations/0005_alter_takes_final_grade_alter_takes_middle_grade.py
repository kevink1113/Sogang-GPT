# Generated by Django 4.2.11 on 2024-04-07 09:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lecture', '0004_alter_course_advisor_alter_course_classroom_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='takes',
            name='final_grade',
            field=models.CharField(max_length=4, null=True),
        ),
        migrations.AlterField(
            model_name='takes',
            name='middle_grade',
            field=models.CharField(max_length=4, null=True),
        ),
    ]