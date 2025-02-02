# Generated by Django 4.2.9 on 2024-02-03 12:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0010_class_section'),
    ]

    operations = [
        migrations.CreateModel(
            name='AcademicYear',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('academic_year', models.CharField(max_length=10, unique=True)),
            ],
            options={
                'verbose_name': 'AcademicYear',
                'verbose_name_plural': 'AcademicYears',
            },
        ),
        migrations.AlterField(
            model_name='section',
            name='section_name',
            field=models.CharField(max_length=50, unique=True),
        ),
    ]
