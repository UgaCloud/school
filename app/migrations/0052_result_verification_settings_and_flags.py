from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0051_alter_academicclassstream_class_teacher_signature'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ResultVerificationSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pass_mark_percent', models.DecimalField(decimal_places=2, default=50.0, max_digits=5)),
                ('boundary_window', models.DecimalField(decimal_places=2, default=5.0, max_digits=5)),
                ('sample_percent', models.DecimalField(decimal_places=2, default=10.0, max_digits=5)),
                ('outlier_percent', models.DecimalField(decimal_places=2, default=5.0, max_digits=5)),
                ('enable_sampling', models.BooleanField(default=True)),
                ('enable_boundary', models.BooleanField(default=True)),
                ('enable_outlier', models.BooleanField(default=True)),
            ],
        ),
        migrations.AddField(
            model_name='result',
            name='verification_status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('FLAGGED', 'Flagged'), ('VERIFIED', 'Verified')], default='PENDING', max_length=10),
        ),
        migrations.AddField(
            model_name='result',
            name='is_sampled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='result',
            name='is_boundary',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='result',
            name='is_outlier',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='result',
            name='verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='result',
            name='verified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_results', to=settings.AUTH_USER_MODEL),
        ),
    ]
