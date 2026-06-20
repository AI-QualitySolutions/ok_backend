from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('access_point', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='router',
            name='name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
