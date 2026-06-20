from rest_framework.permissions import BasePermission

from authentication.models import (
    Company,
    MyUser
)


from rest_framework.permissions import BasePermission

class OrPermission(BasePermission):

    def __init__(self, *permissions):
        self.permissions = permissions

    def has_permission(self, request, view):
        return any(permission().has_permission(request, view) for permission in self.permissions)

    def has_object_permission(self, request, view, obj):
        return any(permission().has_object_permission(request, view, obj) for permission in self.permissions)


class TemperaturePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return user.company and user.company.is_temperature
        if user.is_staff:
            return user.is_temperature
        return False

class GuardPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return user.company and user.company.is_guard
        if user.is_staff:
            return user.is_guard
        return False

class PeopleCountPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return user.company and user.company.is_peoplecount
        if user.is_staff:
            return user.is_peoplecount
        return False

class KitchenPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return user.company and user.company.is_kitchen
        if user.is_staff:
            return user.is_kitchen
        return False

class AGGFPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return user.company and user.company.is_aggf
        if user.is_staff:
            return user.is_aggf
        return False

class FoodWeightPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return user.company and user.company.is_foodweight
        if user.is_staff:
            return user.is_foodweight
        return False


class CleannessPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return user.company and user.company.is_cleanness
        if user.is_staff:
            return user.is_cleanness
        return False


class RecyclePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return user.company and user.company.is_recycle
        if user.is_staff:
            return user.is_recycle
        return False


class BuffetPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return user.company and user.company.is_buffet
        if user.is_staff:
            return user.is_buffet
        return False

class CleanersPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return user.company and user.company.is_cleaners
        if user.is_staff:
            return user.is_cleaners
        return False


class SentimentPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return user.company and user.company.is_sentiment
        if user.is_staff:
            return user.is_sentiment
        return False


class WaterTankPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return user.company and user.company.is_water_tank
        if user.is_staff:
            return user.is_water_tank
        return False


class CanDeleteImagePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return bool(user.is_can_delete_image)


class AccessPointPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return user.company and user.company.is_accesspoint
        if user.is_staff:
            return user.is_accesspoint
        return False


class CleanersPresencePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return user.company and user.company.is_cleaners_presence
        if user.is_staff:
            return user.is_cleaners_presence
        return False
