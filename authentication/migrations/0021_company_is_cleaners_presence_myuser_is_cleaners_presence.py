from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0020_company_is_accesspoint_myuser_is_accesspoint'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='is_cleaners_presence',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='myuser',
            name='is_cleaners_presence',
            field=models.BooleanField(default=False),
        ),
    ]
