# Generated by Django 4.2.9 on 2024-07-23 04:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0029_term_academic_year_term_is_current_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='BillItem',
            new_name='StudentBillItem',
        ),
    ]
