import csv
import io
from datetime import datetime
import pytz
from django.contrib import admin, messages
from django.shortcuts import render
from django.urls import path
from django.http import HttpResponseRedirect
from .models import CounterHistory, Camera
from authentication.models import Company

riyadh_tz = pytz.timezone("Asia/Riyadh")

def parse_datetime_from_parts(date_str, time_str):
    datetime_str = f"{date_str} {time_str}"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            naive_dt = datetime.strptime(datetime_str, fmt)
            return riyadh_tz.localize(naive_dt)
        except ValueError:
            continue
    raise ValueError(f"Invalid datetime format: {datetime_str}")

@admin.register(CounterHistory)
class CounterHistoryAdmin(admin.ModelAdmin):
    search_fields = ['id', "sn", "camera__id", "camera__sn"]
    list_display = ['id', 'camera', 'total_in', 'total_out', "start_time", "end_time", 'created_at']
    list_filter = ['created_at', "camera__tent__company__name"]
    change_list_template = "admin/counterhistory_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-csv/', self.admin_site.admin_view(self.upload_csv), name='counterhistory_upload_csv'),
        ]
        return custom_urls + urls

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "camera":
            kwargs["queryset"] = Camera.objects.filter(type="peoplecount")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def upload_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")


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
            for row in reader:
                try:
                    camera_sn = row["camera_sn"].strip()
                    total_in = int(row["enter"])
                    total_out = int(row["exit"])
                    date = row["date"].strip()
                    start_time = row["start_time"].strip()
                    end_time = row["end_time"].strip()

                    camera = Camera.objects.get(sn=camera_sn)
                    if not camera:
                        self.message_user(
                            request,
                            f"Camera not found for SN '{camera_sn}'",
                            level=messages.WARNING
                        )
                        continue

                    start_dt = parse_datetime_from_parts(date, start_time)
                    end_dt = parse_datetime_from_parts(date, end_time)

                    CounterHistory.objects.create(
                        camera=camera,
                        sn=camera_sn,
                        total_in=total_in,
                        total_out=total_out,
                        start_time=start_dt,
                        end_time=end_dt,
                    )

                    success_count += 1

                except Exception as e:
                    self.message_user(request, f"Error in row {row}: {str(e)}", level=messages.ERROR)

            self.message_user(request, f"Successfully imported {success_count} rows.", level=messages.SUCCESS)
            return HttpResponseRedirect("..")

        context = dict(
            self.admin_site.each_context(request),
            company_list=Company.objects.all(),
        )
        return render(request, "admin/upload_csv_form.html", context)
