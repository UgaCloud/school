# Generated by Django 4.2.9 on 2024-08-11 08:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0035_remove_studentbill_academic_year_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='billitem',
            name='bill_duration',
            field=models.CharField(choices=[('None', 'None'), ('Termly', 'Termly'), ('Annually', 'Annually')], max_length=50),
        ),
        migrations.AlterField(
            model_name='billitem',
            name='category',
            field=models.CharField(choices=[('One Off', 'One Off'), ('Recurring', 'Recurring')], max_length=50),
        ),
        migrations.AlterField(
            model_name='billitem',
            name='description',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='billitem',
            name='item_name',
            field=models.CharField(max_length=50),
        ),
    ]
