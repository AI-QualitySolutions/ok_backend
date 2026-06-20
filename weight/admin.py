from django.contrib import admin
from weight.models import OrderWeight, WeightConditions, EnvironmentSensor
# admin.py
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django import forms
import csv

@admin.register(WeightConditions)
class WeightConditionsAdmin(admin.ModelAdmin):
    search_fields = ['start_date']
    list_display = ['id', 'breakfast_start', 'breakfast_end',  'breakfast_weight_accepted', 'lunch_start', 'lunch_end', 'lunch_weight_accepted', 'dinner_start', 'dinner_end', 'dinner_weight_accepted']

# @admin.register(OrderWeight)
# class OrderWeightAdmin(admin.ModelAdmin):
#     search_fields = ['date', 'weight_sensor__tent__company__name', 'weight_sensor__tent__name']
#     list_display = ['id', 'weight_sensor', 'weight', 'date', 'created_at']
#     list_filter = ['created_at', "weight_sensor"]

#     def formfield_for_foreignkey(self, db_field, request, **kwargs):
#         if db_field.name == "weight_sensor":
#             kwargs["queryset"] = EnvironmentSensor.objects.filter(type="weight")
#         return super().formfield_for_foreignkey(db_field, request, **kwargs)


import csv
import io
from datetime import datetime, timedelta
import pytz
from django.contrib import admin, messages
from django.shortcuts import render
from django.urls import path
from django.http import HttpResponseRedirect
from .models import OrderWeight, EnvironmentSensor
from authentication.models import Company
from tent.models import Tent
import random

riyadh_tz = pytz.timezone("Asia/Riyadh")

def parse_datetime(date_str, time_str):
    datetime_str = f"{date_str} {time_str}"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            naive_dt = datetime.strptime(datetime_str, fmt)
            # Make datetime aware in Riyadh timezone
            aware_dt = riyadh_tz.localize(naive_dt)
            return aware_dt
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {datetime_str}")
class OrderWeightAdmin(admin.ModelAdmin):
    change_list_template = "admin/orderweight_changelist.html"
    list_display = ("device_num", "weight", "date", "weight_sensor")
    list_filter = ("weight_sensor__tent__name", "device_num", "date")
    search_fields = ("device_num", "weight_sensor__sn", "weight_sensor__tent__name")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-csv/', self.admin_site.admin_view(self.upload_csv), name='orderweight_orderweight_upload_csv'),
        ]
        return custom_urls + urls

    def upload_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            company_id = 1

            if not company_id:
                self.message_user(request, "No company selected.", level=messages.ERROR)
                return HttpResponseRedirect(request.path_info)
            try:
                company = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                self.message_user(request, "Selected company does not exist.", level=messages.ERROR)
                return HttpResponseRedirect(request.path_info)
            if not csv_file:
                self.message_user(request, "No file uploaded.", level=messages.ERROR)
                return HttpResponseRedirect(request.path_info)

            if not csv_file.name.endswith(".csv"):
                self.message_user(request, "Only CSV files are accepted.", level=messages.ERROR)
                return HttpResponseRedirect(request.path_info)

            decoded_file = csv_file.read().decode("utf-8")
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            success_count = 0
            riyadh_tz = pytz.timezone("Asia/Riyadh")

            for row in reader:
                try:
                    office_number = row["officeNumber"].strip()
                    device_number = row.get("deviceNumber", "").strip() or None
                    weight = float(row["weight"])
                    count = row["count"].strip()

                    # # Combine date and time, then localize to Riyadh timezone
                    # datetime_str = f"{date} {time}"
                    # date_time_naive = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                    # date_time = riyadh_tz.localize(date_time_naive)
                    date_time = parse_datetime(row["date"].strip(), row["time"].strip())

                    # Get sensor
                    if device_number:
                        weight_sensor = EnvironmentSensor.objects.filter(
                            tent__name=office_number,
                            tent__company=company,
                            type="weight",
                            sn=device_number
                        ).first()
                    else:
                        weight_sensor = EnvironmentSensor.objects.filter(
                            tent__name=office_number,
                            tent__company=company,
                            type="weight"
                        ).first()

                    if not weight_sensor:
                        self.message_user(
                            request,
                            f"Sensor not found for Tent '{office_number}' and Device '{device_number}'.",
                            level=messages.WARNING
                        )
                        continue
                    objects_to_create = []

                    for i in range(int(count)):
                        added_time = random.randint(0, 4)
                        date = date_time + timedelta(minutes=added_time)
                        obj = OrderWeight(
                            device_num=device_number or "",
                            weight=weight,
                            date=date,
                            weight_sensor=weight_sensor
                        )
                        objects_to_create.append(obj)
                        
                    OrderWeight.objects.bulk_create(objects_to_create)

 
                    success_count += 1

                except Exception as e:
                    self.message_user(request, f"Error in row {row}: {str(e)}", level=messages.ERROR)

            self.message_user(request, f"Successfully imported {success_count} rows.", level=messages.SUCCESS)
            return HttpResponseRedirect("..")

        context = dict(
            self.admin_site.each_context(request),
            company_list = Company.objects.all(),
        )
        return render(request, "admin/upload_csv_form.html", context)

admin.site.register(OrderWeight, OrderWeightAdmin)
