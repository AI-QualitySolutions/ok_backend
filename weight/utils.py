from django.conf import settings
from django.core.exceptions import PermissionDenied
from decouple import config

def match_add_new_order_secret_key(provided_key):

    if settings.ADD_NEW_ORDER_KEY != provided_key:
        raise PermissionDenied("Invalid secret key.")
    return True

def match_water_level_key(provided_key):
    if settings.WATER_LEVEL_KEY != provided_key:
        raise PermissionDenied("Invalid water level secret key.")
    return True

def match_temperature_key(provided_key):
    if settings.TEMPERATURE_KEY != provided_key:
        raise PermissionDenied("Invalid temperature secret key.")
    return True

def match_people_count_key(provided_key):
    if settings.PEOPLE_COUNT_KEY != provided_key:
        raise PermissionDenied("Invalid people count secret key.")
    return True

def match_guard_detection_key(provided_key):
    if settings.GUARD_DETECTION_KEY != provided_key:
        raise PermissionDenied("Invalid guard detection secret key.")
    return True

def match_garbage_detection_key(provided_key):
    if settings.GARBAGE_DETECTION_KEY != provided_key:
        raise PermissionDenied("Invalid garbage detection secret key.")
    return True


def match_recycle_detection_key(provided_key):
    if settings.RECYCLE_DETECTION_KEY != provided_key:
        raise PermissionDenied("Invalid recycle detection secret key.")
    return True


def match_kitchen_camera_key(provided_key):
    if settings.KITCHEN_CAMERA_KEY != provided_key:
        raise PermissionDenied("Invalid kitchen camera secret key.")
    return True

def match_aggf_camera_key(provided_key):
    if settings.AGGF_CAMERA_KEY != provided_key:
        raise PermissionDenied("Invalid aggf camera secret key.")
    return True

def match_smoking_camera_key(provided_key):
    if settings.AGGF_CAMERA_KEY != provided_key:
        raise PermissionDenied("Invalid aggf camera secret key.")
    return True

def match_face_detection_camera_key(provided_key):
    if settings.FACE_DETECTION_KEY != provided_key:
        raise PermissionDenied("Invalid face detection camera secret key.")
    return True

def match_garbage_monitoring_key(provided_key):
    if settings.GARBAGE_MONITORING_KEY != provided_key:
        raise PermissionDenied("Invalid garbage monitoring secret key.")
    return True


def match_buffet_violation_key(provided_key):
    if settings.BUFFET_VIOLATION_KEY != provided_key:
        raise PermissionDenied("Invalid garbage detection secret key.")
    return True

def match_cleaners_detection_key(provided_key):
    if settings.BATHROOM_MONITORING_KEY != provided_key:
        raise PermissionDenied("Invalid guard detection secret key.")
    return True

def match_sentiment_analysis_key(provided_key):
    if settings.SENTIMENT_ANALYSIS_KEY != provided_key:
        raise PermissionDenied("Invalid guard detection secret key.")
    return True

def match_camera_key(provided_key):
    if settings.CAMERA_SECRET_KEY != provided_key:
        raise PermissionDenied("Invalid guard detection secret key.")
    return True


def match_empty_chair_detection_key(provided_key):
    if settings.EMPTY_CHAIR_DETECTION_KEY != provided_key:
        raise PermissionDenied("Invalid empty chair detection secret key.")
    return True
