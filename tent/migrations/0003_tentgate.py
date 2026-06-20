from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tent', '0002_alter_country_created_at_alter_country_updated_at_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='TentGate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
                ('name', models.CharField(max_length=100)),
                ('tent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gates', to='tent.tent')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
