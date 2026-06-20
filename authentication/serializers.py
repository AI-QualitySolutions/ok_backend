from django.contrib.auth import get_user_model

from rest_framework import serializers

from authentication.models import MyUser, Company

from tent.models import Tent
from camera.models import CameraType


class CompanySerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = ("id","company_name", "logo", "icon", "name", "name_ar")

    def get_company_name(self, obj):
        return obj.name


    def get_logo(self, obj):
        request = self.context.get('request')
        if request and obj.logo:
            return request.build_absolute_uri(obj.logo.url)
        return None


    def get_icon(self, obj):
        request = self.context.get('request')
        if request and obj.icon:
            return request.build_absolute_uri(obj.icon.url)
        return None

class PermissionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        exclude = ("logo", "name", "name_ar")


class UserPermissionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        exclude = ("company", "email", "username", "date_joined",
                   "last_login", "sensor_update_permission", "assigned_tent", "is_superuser", "is_active", "is_staff", "is_admin", "password", "id")


class UserLoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        style={'input_type': 'password'}, write_only=True, required=True)

    class Meta:
        model = get_user_model()
        fields = ('email', 'password')

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        # Check for required fields
        if not email:
            raise serializers.ValidationError({"email": "Email is required."})
        if not password:
            raise serializers.ValidationError(
                {"password": "Password is required."})

        User = get_user_model()
        try:
            user = MyUser.objects.get(email=email)
        except MyUser.DoesNotExist:
            raise serializers.ValidationError(
                {"user": "User with this Email does not exist."})

        if not user.check_password(password):
            raise serializers.ValidationError({"invalid": "Invalid password."})

        attrs['user'] = user
        return attrs


class UserRegistrationSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(
        style={"input_type": "password"}, write_only=True)
    tent_list = serializers.CharField(required=False)

    class Meta:
        model = MyUser
        fields = ["email", "username", "password", "password2", "tent_list", "company", "is_temperature", "is_guard",
                  "is_peoplecount", "is_kitchen", "is_aggf", "is_falldetection", "is_violencedetection", "is_crowdmonitoring",  "is_climbmonitoring", "is_abnormalactivity", "is_foodweight", "is_cleanness", "is_recycle", "is_livestream",
                  "is_buffet", "is_cleaners", "is_sentiment", "is_water_tank", "is_can_delete_image", "is_accesspoint", "is_cleaners_presence"]
        extra_kwargs = {
            "password": {"write_only": True},
            "email": {"validators": []},
            "company": {"required": False},
        }

    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.get('password2')
        if password != password2:
            raise serializers.ValidationError(
                {"password": "Password and Confirm Password are not match"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2', None)
        tent_list = validated_data.pop('tent_list', None)
        company = validated_data.pop('company', None)

        # Extract permission fields separately
        permission_fields = {
            'is_temperature': validated_data.pop('is_temperature', False),
            'is_guard': validated_data.pop('is_guard', False),
            'is_peoplecount': validated_data.pop('is_peoplecount', False),
            'is_kitchen': validated_data.pop('is_kitchen', False),
            'is_aggf' : validated_data.pop('is_aggf', False),
            'is_falldetection': validated_data.pop('is_falldetection', False),
            'is_violencedetection': validated_data.pop('is_violencedetection', False),
            'is_crowdmonitoring': validated_data.pop('is_crowdmonitoring', False),
            'is_climbmonitoring': validated_data.pop('is_climbmonitoring', False),
            'is_abnormalactivity': validated_data.pop('is_abnormalactivity', False),
            'is_livestream': validated_data.pop('is_livestream', False),
            'is_foodweight': validated_data.pop('is_foodweight', False),
            'is_cleanness': validated_data.pop('is_cleanness', False),
            'is_recycle': validated_data.pop('is_recycle', False),
            'is_buffet': validated_data.pop('is_buffet', False),
            'is_cleaners': validated_data.pop('is_cleaners', False),
            'is_sentiment': validated_data.pop('is_sentiment', False),
            'is_water_tank': validated_data.pop('is_water_tank', False),
            'is_can_delete_image': validated_data.pop('is_can_delete_image', False),
            'is_accesspoint': validated_data.pop('is_accesspoint', False),
            'is_cleaners_presence': validated_data.pop('is_cleaners_presence', False),
        }

        # Create the user
        user = MyUser.objects.create_user(**validated_data)

        # Assign permissions
        for field, value in permission_fields.items():
            setattr(user, field, value)

        # Assign the Company instance
        if company:
            user.company = company

        # Handle assigned_tent (ManyToMany)
        if tent_list:
            try:
                tent_ids = [int(id.strip()) for id in tent_list.split(",")]
                tents = Tent.objects.filter(id__in=tent_ids)
                user.assigned_tent.set(tents)
            except:
                raise serializers.ValidationError("Invalid Tent list")

        user.save()
        return user

    def update(self, instance, validated_data):
        # Extract non-model fields from validated_data
        tent_list = validated_data.pop('tent_list', None)
        company = validated_data.pop('company', None)

        # Update core fields using parent implementation
        user = super().update(instance, validated_data)

        # Update ManyToMany: assigned_tent
        user.assigned_tent.clear()
        if tent_list:
            try:
                tent_ids = [int(id.strip()) for id in tent_list.split(",")]
                tents = Tent.objects.filter(id__in=tent_ids)
                user.assigned_tent.set(tents)
            except (ValueError, Tent.DoesNotExist):
                raise serializers.ValidationError(
                    {"tent_list": "Invalid tent IDs provided"})
        user.save()
        return user


class MyUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ("id", "email", "username", "date_joined", "last_login",
                  "is_admin", "is_active", "is_staff", "is_superuser", "assigned_tent")
