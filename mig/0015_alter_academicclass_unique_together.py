# Generated by Django 4.2.9 on 2024-06-12 05:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0014_signature'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='academicclass',
            unique_together={('Class', 'academic_year', 'term')},
        ),
    ]
