# authentication/admin.py
from django.contrib import admin
from authentication.models import MyUser, Company
from authentication.forms import MyUserCreationForm
from tent.models import Tent


@admin.action(description="Assign all company tents to selected users")
def assign_all_company_tents(modeladmin, request, queryset):
    for user in queryset:
        if user.company:
            company_tents = Tent.objects.filter(company=user.company)
            user.assigned_tent.set(company_tents)
    modeladmin.message_user(request, "All company tents assigned successfully.")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


@admin.register(MyUser)
class MyUserAdmin(admin.ModelAdmin):
    add_form = MyUserCreationForm
    actions = [assign_all_company_tents]
    list_display = ('email', 'username', 'is_admin', 'company')
    search_fields = ('email', 'username')
    readonly_fields = ('date_joined', 'last_login')
    filter_horizontal = ('assigned_tent',)

    # Fields for creating a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'company', 'password1', 'password2',
                'is_admin', 'is_active', 'is_staff', 'is_superuser', 'is_annotator',
                'company_annotator', 'camera_type_annotator', 'sensor_update_permission',
                'assigned_tent',
                # Add PermissionModel fields
                'is_temperature',
                'is_guard',
                'is_peoplecount',
                'is_kitchen',
                'is_aggf',
                'is_smoking',
                'is_face_detection',
                'is_falldetection',
                'is_violencedetection',
                'is_crowdmonitoring',
                'is_climbmonitoring',
                'is_abnormalactivity',
                'is_foodweight',
                'is_cleanness',
                'is_recycle',
                'is_buffet',
                'is_cleaners',
                'is_sentiment',
                'is_water_tank',
                'is_sensor_assign',
                'is_annotator_ranking',
                'is_livestream',
                'is_can_delete_image',
                'is_accesspoint',
                'is_cleaners_presence',
                'is_chairdetection',
            ),
        }),
    )

    # Fields for editing an existing user
    fieldsets = (
        (None, {
            'fields': ('email', 'username', 'company')
        }),
        ('Permissions', {
            'fields': (
                'is_admin', 'is_active', 'is_staff', 'is_superuser', 'is_annotator',
                'sensor_update_permission',
                # Add PermissionModel fields
                'is_temperature', 
                'is_guard', 
                'is_peoplecount', 
                'is_kitchen', 
                'is_aggf', 
                'is_smoking', 
                'is_face_detection', 
                'is_falldetection', 
                'is_violencedetection', 
                'is_crowdmonitoring', 
                'is_climbmonitoring',
                'is_abnormalactivity',
                'is_foodweight', 
                'is_cleanness',
                'is_recycle',
                'is_buffet', 
                'is_cleaners', 
                'is_sentiment', 
                'is_water_tank', 
                'is_sensor_assign',
                'is_annotator_ranking',
                'is_livestream',
                'is_can_delete_image',
                'is_accesspoint',
                'is_cleaners_presence',
                'is_chairdetection',
            )
        }),
        ('Associations', {
            'fields': ('company_annotator', 'camera_type_annotator', 'assigned_tent')
        }),
        ('Important dates', {
            'fields': ('date_joined', 'last_login')
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:  # If creating a new user
            return self.add_fieldsets
        return self.fieldsets  # If editing an existing user

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs['form'] = self.add_form
        return super().get_form(request, obj, **kwargs)
