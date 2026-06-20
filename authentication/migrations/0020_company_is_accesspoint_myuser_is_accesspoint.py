from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0019_company_is_can_delete_image_company_is_recycle_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='is_accesspoint',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='myuser',
            name='is_accesspoint',
            field=models.BooleanField(default=False),
        ),
    ]
