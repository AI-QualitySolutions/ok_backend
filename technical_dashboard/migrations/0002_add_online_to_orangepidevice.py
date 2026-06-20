from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('technical_dashboard', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='orangepidevice',
            name='online',
            field=models.BooleanField(default=False),
        ),
    ]
