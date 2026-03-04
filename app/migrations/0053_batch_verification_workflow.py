from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class CreateModelIfMissing(migrations.CreateModel):
    """Create a model table only when it does not already exist."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.name)
        table_name = model._meta.db_table

        with schema_editor.connection.cursor() as cursor:
            if table_name in schema_editor.connection.introspection.table_names(cursor):
                return

        return super().database_forwards(app_label, schema_editor, from_state, to_state)


class AddFieldIfMissing(migrations.AddField):
    """Add a field only when the target column is missing."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        table_name = model._meta.db_table
        field = model._meta.get_field(self.name)
        column_name = field.column

        with schema_editor.connection.cursor() as cursor:
            if table_name not in schema_editor.connection.introspection.table_names(cursor):
                return super().database_forwards(app_label, schema_editor, from_state, to_state)
            existing_columns = {
                col.name
                for col in schema_editor.connection.introspection.get_table_description(cursor, table_name)
            }

        if column_name in existing_columns:
            return

        return super().database_forwards(app_label, schema_editor, from_state, to_state)


class RemoveFieldIfExists(migrations.RemoveField):
    """Remove a field only when the corresponding DB column exists."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.model_name)
        table_name = model._meta.db_table
        field = model._meta.get_field(self.name)
        column_name = field.column

        with schema_editor.connection.cursor() as cursor:
            if table_name not in schema_editor.connection.introspection.table_names(cursor):
                return
            existing_columns = {
                col.name
                for col in schema_editor.connection.introspection.get_table_description(cursor, table_name)
            }

        if column_name not in existing_columns:
            return

        return super().database_forwards(app_label, schema_editor, from_state, to_state)


class AlterFieldIfExists(migrations.AlterField):
    """Alter a field only when the target column exists."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        table_name = model._meta.db_table
        field = model._meta.get_field(self.name)
        column_name = field.column

        with schema_editor.connection.cursor() as cursor:
            if table_name not in schema_editor.connection.introspection.table_names(cursor):
                return
            existing_columns = {
                col.name
                for col in schema_editor.connection.introspection.get_table_description(cursor, table_name)
            }

        if column_name not in existing_columns:
            return

        return super().database_forwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0052_result_verification_settings_and_flags'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        CreateModelIfMissing(
            name='ResultBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('PENDING', 'Pending Verification'), ('VERIFIED', 'Verified'), ('FLAGGED', 'Flagged')], default='DRAFT', max_length=10)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('assessment', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='result_batch', to='app.assessment')),
                ('submitted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='submitted_batches', to=settings.AUTH_USER_MODEL)),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_batches', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        CreateModelIfMissing(
            name='VerificationSample',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dos_mark', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('matched', models.BooleanField(null=True)),
                ('checked_at', models.DateTimeField(blank=True, null=True)),
                ('checked_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='checked_samples', to=settings.AUTH_USER_MODEL)),
                ('result', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='verification_sample', to='app.result')),
            ],
        ),
        AddFieldIfMissing(
            model_name='result',
            name='batch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='results', to='app.resultbatch'),
        ),
        AddFieldIfMissing(
            model_name='result',
            name='status',
            field=models.CharField(choices=[('DRAFT', 'Draft'), ('PENDING', 'Pending Verification'), ('VERIFIED', 'Verified'), ('FLAGGED', 'Flagged')], default='DRAFT', max_length=10),
        ),
        RemoveFieldIfExists(
            model_name='result',
            name='is_boundary',
        ),
        RemoveFieldIfExists(
            model_name='result',
            name='is_outlier',
        ),
        RemoveFieldIfExists(
            model_name='result',
            name='is_sampled',
        ),
        RemoveFieldIfExists(
            model_name='result',
            name='verification_status',
        ),
        RemoveFieldIfExists(
            model_name='result',
            name='verified_at',
        ),
        RemoveFieldIfExists(
            model_name='result',
            name='verified_by',
        ),
        RemoveFieldIfExists(
            model_name='resultverificationsetting',
            name='boundary_window',
        ),
        RemoveFieldIfExists(
            model_name='resultverificationsetting',
            name='enable_boundary',
        ),
        RemoveFieldIfExists(
            model_name='resultverificationsetting',
            name='enable_outlier',
        ),
        RemoveFieldIfExists(
            model_name='resultverificationsetting',
            name='enable_sampling',
        ),
        RemoveFieldIfExists(
            model_name='resultverificationsetting',
            name='outlier_percent',
        ),
        RemoveFieldIfExists(
            model_name='resultverificationsetting',
            name='pass_mark_percent',
        ),
        AddFieldIfMissing(
            model_name='resultverificationsetting',
            name='tolerance_marks',
            field=models.DecimalField(decimal_places=2, default=1.0, max_digits=5),
        ),
        AlterFieldIfExists(
            model_name='resultverificationsetting',
            name='sample_percent',
            field=models.DecimalField(decimal_places=2, default=5.0, max_digits=5),
        ),
    ]
