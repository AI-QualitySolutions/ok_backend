from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('camera', '0036_camera_gate'),
    ]

    operations = [
        # Allow NULL before clearing old CharField values — column was NOT NULL
        migrations.AlterField(
            model_name='recyclemonitoringreport',
            name='annotator_status',
            field=models.CharField(
                blank=True,
                choices=[('clean', 'clean'), ('recycle', 'recycle')],
                default='',
                max_length=10,
                null=True,
            ),
        ),
        # Null out all old CharField values (e.g. 'plastic', 'clean', '')
        # before altering to JSONField — unquoted strings are not valid JSON
        migrations.RunSQL(
            sql="UPDATE camera_recyclemonitoringreport SET annotator_status = NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name='recyclemonitoringreport',
            name='annotator_status',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='recyclemonitoringreport',
            name='violation_list',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
