import os

from django.conf import settings

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hajjtent23DRF.settings")

app = Celery("hajjtent23DRF", broker='redis://localhost:6379/0')
app.conf.enable_utc = False
app.conf.update(timezone="Asia/Riyadh")

app.autodiscover_tasks(['sensor', 'technical_dashboard'])

app.conf.beat_schedule = {
    'collect_sensor_data_every_60_seconds': {
        'task': 'sensor.tasks.collect_sensor_data_task',
        'schedule': 60.0,
    },
    # check device activity (camera, orange pi, access point) heartbeats every 60 seconds
    'check_device_heartbeats_every_60_seconds': {
        'task': 'technical_dashboard.tasks.check_device_heartbeats',
        'schedule': 60.0,
    },
    # sync OrangePi last_seen from ShellHub every 60 seconds
    'sync_shellhub_devices_every_60_seconds': {
        'task': 'technical_dashboard.tasks.sync_shellhub_devices',
        'schedule': 60.0,
    },
    # 'generate_clean_indicator_data_every_300_sec': {
    #     'task': 'camera.tasks.generate_fake_clean_indicator_data',
    #     'schedule': 60.0,
    # },
    # 'generate_fake_guard_presence_data_every_300_sec': {
    #     'task': 'camera.tasks.generate_fake_guard_presence_data',
    #     'schedule': 60.0,
    # },
    # 'generate_fake_kitchen_violation_data_every_300_sec': {
    #     'task': 'camera.tasks.generate_fake_kitchen_violation_data',
    #     'schedule': 60.0,
    # },
    # 'generate_fake_counter_data_300_sec': {
    #     'task': 'camera.tasks.generate_fake_counter_data',
    #     'schedule': 60.0,
    # },
    # 'generate_fake_environment_data_300_sec': {
    #     'task': 'sensor.tasks.generate_fake_environment_data',
    #     'schedule': 60.0,
    # },
    # 'generate_fake_tent_air_quality_300_sec': {
    #     'task': 'tent.tasks.generate_fake_tent_air_quality',
    #     'schedule': 60.0,
    # },
    # 'generate_fake_water_tank_data_300_sec': {
    #     'task': 'tent.tasks.generate_fake_water_tank_data',
    #     'schedule': 60.0,
    # },
    # 'generate_fake_order_weight_data_300_sec': {
    #     'task': 'weight.tasks.generate_fake_order_weight_data',
    #     'schedule': 60.0,
    # },
}

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request}")
