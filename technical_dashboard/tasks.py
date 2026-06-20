import logging
from datetime import timedelta

import pytz
import requests
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

RIYADH_TZ = pytz.timezone("Asia/Riyadh")

SHELLHUB_URL      = "https://shellhub.aiqualitysolutions.com"
SHELLHUB_USERNAME = "aiqualitysolutions"
SHELLHUB_PASSWORD = "AiQuality@2024#"

OFFLINE_THRESHOLD_SECONDS = 120  # 2 minutes


def _get_last_log(device_type, **fk_filter):
    from .models import DeviceActivityLog

    return (
        DeviceActivityLog.objects
        .filter(device_type=device_type, **fk_filter)
        .order_by('-timestamp')
        .first()
    )


def _create_log(device_type, status, now, details=None, **fk_kwargs):
    from .models import DeviceActivityLog

    DeviceActivityLog.objects.create(
        device_type=device_type,
        status=status,
        timestamp=now,
        details=details,
        **fk_kwargs,
    )


def _check_cameras(now, threshold):
    from camera.models import Camera, CameraHeartbeat

    cameras = Camera.objects.all()

    for camera in cameras:
        hb = CameraHeartbeat.objects.filter(camera=camera).first()

        if hb and hb.updated_at and hb.updated_at >= threshold:
            current_status = 'online'
        else:
            current_status = 'offline'

        last_log = _get_last_log('camera', camera=camera)

        if last_log is None or last_log.status != current_status:
            _create_log(
                device_type='camera',
                status=current_status,
                now=now,
                camera=camera,
            )


def _check_orange_pi_devices(now, threshold):
    from .models import OrangePiDevice

    devices = OrangePiDevice.objects.all()

    for device in devices:
        if device.last_seen and device.last_seen >= threshold:
            current_status = 'online'
        else:
            current_status = 'offline'

        last_log = _get_last_log('orange_pi', orange_pi_device=device)

        if last_log is None or last_log.status != current_status:
            _create_log(
                device_type='orange_pi',
                status=current_status,
                now=now,
                orange_pi_device=device,
            )


def _check_access_points(now, threshold):
    from access_point.models import Router, RouterHeartbeat

    routers = Router.objects.all()

    for router in routers:
        latest_hb = (
            RouterHeartbeat.objects
            .filter(router=router)
            .order_by('-heartbeat_time')
            .first()
        )

        if latest_hb and latest_hb.heartbeat_time and latest_hb.heartbeat_time >= threshold:
            current_status = 'online'
        else:
            current_status = 'offline'

        last_log = _get_last_log('access_point', access_point=router)

        if last_log is None or last_log.status != current_status:
            _create_log(
                device_type='access_point',
                status=current_status,
                now=now,
                access_point=router,
            )


@shared_task
def check_device_heartbeats():
    now = timezone.now().astimezone(RIYADH_TZ)
    threshold = now - timedelta(seconds=OFFLINE_THRESHOLD_SECONDS)

    _check_cameras(now, threshold)
    _check_orange_pi_devices(now, threshold)
    _check_access_points(now, threshold)

    logger.info("Device heartbeat check completed at %s", now)


@shared_task
def sync_shellhub_devices():
    """
    Pulls all OrangePi device statuses from ShellHub and updates
    online + last_seen directly in the DB.
    Runs every 60 seconds via Celery beat.
    """
    from .models import OrangePiDevice

    # Step 1: Authenticate
    try:
        login_resp = requests.post(
            f"{SHELLHUB_URL}/api/login",
            json={"username": SHELLHUB_USERNAME, "password": SHELLHUB_PASSWORD},
            timeout=10,
        )
        login_resp.raise_for_status()
        token = login_resp.json().get("token")
        if not token:
            logger.error("[ShellHub] Login succeeded but no token returned.")
            return
    except Exception as e:
        logger.error(f"[ShellHub] Login failed: {e}")
        return

    # Step 2: Fetch all devices
    try:
        devices_resp = requests.get(
            f"{SHELLHUB_URL}/api/devices",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        devices_resp.raise_for_status()
        shellhub_devices = devices_resp.json()
    except Exception as e:
        logger.error(f"[ShellHub] Devices fetch failed: {e}")
        return

    # Step 3: Update online + last_seen directly in DB
    now = timezone.now().astimezone(RIYADH_TZ)
    updated = 0
    for device in shellhub_devices:
        mac       = device.get("identity", {}).get("mac", "").strip().lower()
        is_online = device.get("online", False)
        logger.info(f"[ShellHub] Device mac={mac} online={is_online} raw_keys={list(device.keys())}")

        if not mac:
            continue

        fields = {"online": is_online}
        if is_online:
            fields["last_seen"] = now

        count = OrangePiDevice.objects.filter(mac_address__iexact=mac).update(**fields)
        updated += count

    logger.info(f"[ShellHub] Sync complete — updated {updated} OrangePi device(s).")
