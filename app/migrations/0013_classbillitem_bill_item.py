# Generated by Django 4.2.9 on 2025-03-08 20:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0012_classbillitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='classbillitem',
            name='bill_item',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='app.billitem'),
            preserve_default=False,
        ),
    ]
