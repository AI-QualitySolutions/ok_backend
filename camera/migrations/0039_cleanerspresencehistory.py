from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('camera', '0038_alter_crowdmonitoringreport_annotator_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='CleanersPresenceHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('person_class', models.CharField(choices=[
                    ('cleaner-female', 'Cleaner Female'),
                    ('cleaner-male', 'Cleaner Male'),
                    ('supervisor-female', 'Supervisor Female'),
                    ('supervisor-male', 'Supervisor Male'),
                ], max_length=20)),
                ('cleaner_count', models.IntegerField(default=0)),
                ('start_time', models.DateTimeField(blank=True, null=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='cleaners_presence/%Y/%m/%d/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('camera', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cleaners_presence_histories',
                    to='camera.camera',
                )),
            ],
        ),
    ]
