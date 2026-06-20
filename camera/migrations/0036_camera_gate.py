from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('camera', '0035_alter_camera_type_alter_cameratype_type_and_more'),
        ('tent', '0003_tentgate'),
    ]

    operations = [
        migrations.AddField(
            model_name='camera',
            name='gate',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='cameras',
                to='tent.tentgate',
            ),
        ),
    ]
