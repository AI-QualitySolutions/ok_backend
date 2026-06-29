from tuya_connector import TuyaOpenAPI
import json
from django.core.management.base import BaseCommand

from sensor.models import EnvironmentSensor, EnvironmentSensorRecord
from tent.models import Tent
from random import randint
from datetime import datetime, timedelta
from django.db import connection
from django.utils import timezone
from datetime import datetime
import pytz
from django.utils.timezone import make_aware
from utils.time import Current_saudi_time
cursor = connection.cursor()


ACCESS_ID = "pcr8574a58jt8rmaw73c"
ACCESS_KEY = "ae56687fc8da4c698b0b29dbd8bdc908"
API_ENDPOINT = "https://openapi.tuyaeu.com"
DEVICE_ID = "bfef641d8e8b4c0ab87brq"


KEY_LIST = [
    # "eu1746729129291OyWI4",
    # "eu1747408899763OwlTQ",
    # "eu1747423236955EE7fg",
    # "eu1747487724252QvYs7",
    # "eu1747488031573sGUAE",
    # "eu1747488140669EAypW",
    # "eu1747488331487OCG7y",
    # "eu1747490546117oyfA5",
    # "eu17476131747074z5jE",
    # "eu1747613388962a70HC",
    # "eu1747613706790Z6p8Y",
    # "eu1747666097803PXnXL",
    # "eu1747758101783ZZFvW",
    # "eu1747766271859SAyrU",
    # "eu17478510076209I4Ay",
    # "eu1747851276585NNMNg",
    # "eu1747851616982TrTkc",
    # "eu1747851794695FLnNu",
    # "eu1747851921408IZXjv",
    # "eu1747852076000JcSr1",
    # "eu17478526264503MSSo",
    # "eu1747854372811pF0c7",
    # "eu1747854735441Jjk5A",
    # "eu1747854919993CXtYm",
    # "eu1747855133701sWcJC",
    # "eu17478565075381aWfl",
    # "eu1747856850884yFD62",
    # "eu1747857130492JUHtA",
    # "eu1747857427733a4sFh",
    # "eu1747857680437VNh97",
    # "eu1747858614961pI8nK",
    # "eu1747861442339fqSAp",
    # "eu1747861674901XQAVk",
    # "eu1747861858575sjJpj",
    # "eu1747862059443qB426",
    # "eu1747862246829f2Nzl",
    # "eu1747938788196ouX3q",
    # "eu1748278444935QA7bx",
    "eu1756998511577kAvvo", # mohamed231969@outlook.sa
    "eu1777736513953R8gY3", # sensor_ai@outlook.com
    "eu1777812674314MqV08",
    "eu1631029393503Ac9ox", # Sensor farm
    "eu1767183585804GFUar"
]


def get_tent(item):
    try:
        name = item.split('-')[0]
        tent_list = Tent.objects.filter(name=name)
        if tent_list.exists():
            return tent_list[0]
        else:
            return None
    except:
        return None


def set_data(response):
    _, end_time = Current_saudi_time()
    if response["success"]:
        for item in response["result"]:
            # --- START NEW LOGIC FOR CATEGORY MISMATCH ---
            temp_val = None
            hum_val = None
            
            # Use a dictionary lookup for speed and safety
            status_data = {s['code']: s['value'] for s in item.get('status', [])}
            category = item.get('category')
            
            if category == 'wsdcg':
                temp_val = status_data.get('va_temperature', 0) / 10
                hum_val = status_data.get('va_humidity', 0)
            elif category == 'cs':
                # For 'cs', tempdisp and humdisp are the reliable fields
                temp_val = status_data.get('CURRENTTEMP', 0) / 10
                hum_val = status_data.get('envhumid', 0) / 10 # Adjust if 'cs' humidity isn't /10
            elif category == 'zwjcy':
                temp_val = status_data.get('temp_current', 0) / 10
                hum_val = status_data.get('humidity', 0)
            """
            if category == 'cs':
                # For 'cs', tempdisp and humdisp are the reliable fields
                temp_val = status_data.get('CURRENTTEMP', 0) / 10
                hum_val = status_data.get('envhumid', 0) / 10 # Adjust if 'cs' humidity isn't /10
            """
            # If we couldn't find status data, skip this item to avoid crash
            if temp_val is None and item.get('online'):
                continue
            # --- END NEW LOGIC ---

            update_from_neighbour = False
            try:
                sensor = EnvironmentSensor.objects.get(sn=item["uuid"])
                sensor.name = item["name"]
                
                if item['online'] == True:
                    sensor.tempareture = temp_val # Use calculated temp
                    sensor.humidity = hum_val       # Use calculated humidity
                    sensor.last_entry_time = end_time
                    sensor.online = item['online']
                
                elif not item['online'] and not sensor.check_neighbour:
                    sensor.online = item['online']
                    sensor.save()
                    continue
                
                elif not item['online'] and sensor.check_neighbour:
                    sensor.online = item['online']
                    
                    neighbour_name_1 = sensor.neighbour_name_1
                    neighbour_name_2 = sensor.neighbour_name_2
                    neighbour_name_3 = sensor.neighbour_name_3
                    
                    count = 0
                    total_temperature = 0
                    total_humidity = 0
                    
                    if neighbour_name_1 == None and neighbour_name_2 == None and neighbour_name_3 == None:
                        sensor.save()
                        continue
                    else:
                        if neighbour_name_1 != None and neighbour_name_1.online:
                            count += 1
                            total_temperature += neighbour_name_1.tempareture
                            total_humidity += neighbour_name_1.humidity
                        
                        if neighbour_name_2 != None and neighbour_name_2.online:
                            count += 1
                            total_temperature += neighbour_name_2.tempareture
                            total_humidity += neighbour_name_2.humidity

                        if neighbour_name_3 != None and neighbour_name_3.online:
                            count += 1
                            total_temperature += neighbour_name_3.tempareture
                            total_humidity += neighbour_name_3.humidity
                        
                        if count > 0:
                            sensor.tempareture = round(total_temperature / count, 1)
                            sensor.humidity = round(total_humidity / count, 1)
                            sensor.last_entry_time = end_time
                            update_from_neighbour = True
                        else:
                            sensor.save()
                            continue

                sensor.save()
                EnvironmentSensorRecord.objects.create(
                    sensor=sensor,
                    tempareture=sensor.tempareture,
                    humidity=sensor.humidity,
                    last_entry_time=sensor.last_entry_time,
                    update_from_neighbour=update_from_neighbour
                )
            
            except EnvironmentSensor.DoesNotExist:
                sensor = EnvironmentSensor(
                    sn=item["uuid"],
                    name=item["name"],
                    ip=item.get("ip", ""),
                    lat=item.get("lat", ""),
                    long=item.get("lon", ""),
                )
                if item['online']:
                    sensor.tempareture = temp_val
                    sensor.humidity = hum_val
                    sensor.last_entry_time = end_time
                    sensor.online = True
                    sensor.save()
                    
                    EnvironmentSensorRecord.objects.create(
                        sensor=sensor,
                        tempareture=temp_val,
                        humidity=hum_val,
                        last_entry_time=end_time,
                    )
                else:
                    sensor.online = False
                    sensor.save()


class Command(BaseCommand):
    def handle(self, *args, **options):
        openapi = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_KEY)
        openapi.connect()
        for key in KEY_LIST:
            response = openapi.get(f"/v1.0/users/{key}/devices")

            set_data(response)
