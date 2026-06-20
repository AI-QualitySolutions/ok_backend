
import cv2
import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from celery import shared_task
from django.core.files.base import ContentFile

from camera.models import Camera, CleanIndicatorHistory, GuardPresenceHistory, KitchenViolationReport, CounterHistory, CameraHeartbeat
import time
import random

from camera.serializers import CreateCounterHistorySerializer
from camera.models import Camera, KitchenImage
from tent.models import Tent
from camera.utils import process_kitchen_image
from camera.serializers import KitchenImageSerializer
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def insert_camera_data_func(self, data):
    time.sleep(0.05)
    td = datetime(2023, 6, 26, 0, 0, 0)
    try:
        start_time = data.get("startTime", None)
        start_time = datetime.fromtimestamp(start_time)
        if start_time < td:
            return "Error"
        end_time = data.get("endTime")
        end_time = datetime.fromtimestamp(end_time)
        if end_time < td:
            return "Error"
    except:
        pass
    serializer = CreateCounterHistorySerializer(data=data)
    if serializer.is_valid():
        serializer.save()

        return "Done"
    else:
        return "Error"


# @shared_task
# def save_kitchen_image(tent_id, camera_id, location, image_path):
#     try:
#         # Retrieve related objects (Tent and Camera)
#         tent = Tent.objects.get(id=tent_id)
#         camera = Camera.objects.get(id=camera_id)

#         # Retrieve the image from storage
#         image = default_storage.open(image_path)

#         # Create the KitchenImage instance
#         kitchen_image = KitchenImage(
#             tent=tent,
#             camera=camera,
#             image=image,
#             location=location
#         )
#         kitchen_image.save()

#         # Optionally, remove the image from temporary storage after processing
#         default_storage.delete(image_path)

#         return kitchen_image.id
#     except Exception as e:
#         # Log the error or send it to a monitoring system

#         raise e  # Re-raise the exception so Celery knows the task failed



@shared_task
def generate_fake_clean_indicator_data():
    now = timezone.now()
    cameras = Camera.objects.filter(type="clean")

    for camera in cameras:

        start_time = now
        end_time = start_time + timedelta(seconds=300)
        is_clean = np.random.choice([True, False])

        # Convert numpy boolean to Python boolean if necessary
        is_clean = bool(is_clean)

        if not is_clean:
            # Create image with OpenCV
            img = np.zeros((200, 400, 3), dtype=np.uint8)
            text = f"Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
            cv2.putText(img, text, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Save image to memory buffer
            _, buffer = cv2.imencode('.jpg', img)
            image_content = ContentFile(buffer.tobytes(), name=f"{camera.sn}_{int(start_time.timestamp())}.jpg")
            logger.info(f"Generated image content: {image_content.name}")
        else:
            image_content = None

        # Save record
        CleanIndicatorHistory.objects.create(
            camera=camera,
            is_clean=is_clean,
            start_time=start_time,
            end_time=end_time,
            image=image_content
        )

        # camera hearbeat
        camera_heartbeat, _ = CameraHeartbeat.objects.get_or_create(camera=camera)
        camera_heartbeat.sn = camera.sn
        camera_heartbeat.time = timezone.now()
        camera_heartbeat.save()

@shared_task
def generate_fake_guard_presence_data():
    now = timezone.now()
    cameras = Camera.objects.filter(type="guard")  # Adjust filter as needed

    for camera in cameras:
        start_time = now
        end_time = start_time + timedelta(seconds=300)

        # Generate random presence status
        present = np.random.choice([True, False])
        present = bool(present)  # Convert to Python boolean
        guard_count = random.randint(1, 5) if present else 0

        if present:
            # Green background for presence
            bg_color = (0, 255, 0)  # BGR format (green)
        else:
            # Red background for absence
            bg_color = (0, 0, 255)  # BGR format (red)

        # Create image with colored background
        img = np.zeros((200, 400, 3), dtype=np.uint8)
        img[:] = bg_color

        # Add text overlay
        text = f"Guards: {guard_count} | {start_time.strftime('%H:%M:%S')}"
        cv2.putText(
            img,
            text,
            (10, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),  # White text
            2
        )

        # Save image to buffer
        _, buffer = cv2.imencode('.jpg', img)
        image_content = ContentFile(
            buffer.tobytes(),
            name=f"guard_{camera.sn}_{int(start_time.timestamp())}.jpg"
        )

        # Create history record
        GuardPresenceHistory.objects.create(
            camera=camera,
            guard_count=guard_count,
            present=present,
            start_time=start_time,
            end_time=end_time,
            image=image_content
        )

        # camera hearbeat
        camera_heartbeat, _ = CameraHeartbeat.objects.get_or_create(camera=camera)
        camera_heartbeat.sn = camera.sn
        camera_heartbeat.time = timezone.now()
        camera_heartbeat.save()

        logger.info(f"Created guard presence record: {present} (Count: {guard_count})")

@shared_task
def generate_fake_kitchen_violation_data():
    now = timezone.now()
    cameras = Camera.objects.filter(type="kitchen")
    possible_violations = [
        "No Head Covering",
        "Missing Gloves",
        "Dirty Surface",
        "Uncovered Food",
        "Pests Observed",
        "Improper Storage"
    ]

    for camera in cameras:
        start_time = now
        end_time = start_time + timedelta(seconds=300)
        has_violation = np.random.choice([True, False])
        has_violation = bool(has_violation)

        # Generate violation list if violation exists
        violation_list = None
        if has_violation:
            num_violations = random.randint(1, 3)
            violation_list = random.sample(possible_violations, num_violations)

        # Create image with color coding
        img = np.zeros((400, 600, 3), dtype=np.uint8)  # Larger image for text
        text_color = (255, 255, 255)  # White text

        if has_violation:
            img[:] = (0, 0, 255)  # Red background (BGR)
            text_lines = ["VIOLATIONS DETECTED:", *violation_list]
        else:
            img[:] = (0, 255, 0)  # Green background
            text_lines = ["NO VIOLATIONS DETECTED"]

        # Add multi-line text
        y_position = 50
        for line in text_lines:
            cv2.putText(
                img,
                line,
                (20, y_position),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                text_color,
                1
            )
            y_position += 40

        # Add timestamp
        cv2.putText(
            img,
            start_time.strftime("%Y-%m-%d %H:%M:%S"),
            (20, 380),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            text_color,
            1
        )

        # Save image
        _, buffer = cv2.imencode('.jpg', img)
        image_content = ContentFile(
            buffer.tobytes(),
            name=f"kitchen_{camera.sn}_{int(start_time.timestamp())}.jpg"
        )

        # Create report
        KitchenViolationReport.objects.create(
            camera=camera,
            violation=has_violation,
            violation_list=violation_list,
            start_time=start_time,
            end_time=end_time,
            image=image_content
        )
        # camera hearbeat
        camera_heartbeat, _ = CameraHeartbeat.objects.get_or_create(camera=camera)
        camera_heartbeat.sn = camera.sn
        camera_heartbeat.time = timezone.now()
        camera_heartbeat.save()
        logger.info(f"Created kitchen violation report: {has_violation}")



@shared_task
def generate_fake_counter_data():
    now = timezone.now()
    cameras = Camera.objects.all()

    for camera in cameras:
        start_time = now
        end_time = start_time + timedelta(minutes=15)

        # Generate random traffic data
        def generate_counts():
            return {
                'adult': random.randint(0, 20),
                'child': random.randint(0, 10)
            }

        in_counts = generate_counts()
        out_counts = generate_counts()
        passby_counts = generate_counts()
        turnback_counts = generate_counts()


        # Create record
        CounterHistory.objects.create(
            camera=camera,
            sn=camera.sn,
            total_in=in_counts['adult'] + in_counts['child'],
            total_out=out_counts['adult'] + out_counts['child'],
            passby=passby_counts['adult'] + passby_counts['child'],
            turnback=turnback_counts['adult'] + turnback_counts['child'],
            avg_stay_time=random.randint(2, 45),
            in_adult=in_counts['adult'],
            out_adult=out_counts['adult'],
            passby_adult=passby_counts['adult'],
            turnback_adult=turnback_counts['adult'],
            in_child=in_counts['child'],
            out_child=out_counts['child'],
            passby_child=passby_counts['child'],
            turnback_child=turnback_counts['child'],
            total=(in_counts['adult'] + in_counts['child']),
            start_time=start_time,
            end_time=end_time
        )
        # camera hearbeat
        camera_heartbeat, _ = CameraHeartbeat.objects.get_or_create(camera=camera)
        camera_heartbeat.sn = camera.sn
        camera_heartbeat.time = timezone.now()
        camera_heartbeat.save()
        logger.info(f"Created counter record with image for {camera.sn}")

