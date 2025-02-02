# Generated by Django 4.2.9 on 2024-06-11 17:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0013_currency_schoolsetting_alter_academicclass_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Signature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.CharField(max_length=25)),
                ('signature', models.ImageField(upload_to='signatures')),
            ],
            options={
                'verbose_name': 'Signature',
                'verbose_name_plural': 'Signatures',
            },
        ),
    ]
