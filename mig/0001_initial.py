# Generated by Django 4.2.9 on 2024-01-23 12:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Class',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('code', models.CharField(max_length=3)),
            ],
            options={
                'verbose_name': 'Class',
                'verbose_name_plural': 'Classs',
            },
        ),
        migrations.CreateModel(
            name='Stream',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stream', models.CharField(max_length=10)),
            ],
            options={
                'verbose_name': 'stream',
                'verbose_name_plural': 'streams',
            },
        ),
        migrations.CreateModel(
            name='AcademicClass',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('academic_year', models.CharField(max_length=10)),
                ('term', models.IntegerField()),
                ('fees_amount', models.IntegerField()),
                ('_class', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.class')),
            ],
            options={
                'verbose_name': 'AcademicClass',
                'verbose_name_plural': 'AcademicClasss',
            },
        ),
    ]
