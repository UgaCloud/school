# Generated by Django 4.2.9 on 2025-03-10 07:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0017_delete_classbill'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClassBill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('academic_class', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='class_bills', to='app.academicclass')),
                ('bill_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.billitem')),
            ],
            options={
                'unique_together': {('academic_class', 'bill_item')},
            },
        ),
    ]
