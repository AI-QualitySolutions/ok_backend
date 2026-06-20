from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "Fix environment sensor records by propagating zero-millisecond values."

    def handle(self, *args, **options):
        sql = """
        WITH base AS (
            SELECT 
                ser.id AS sensor_record_id,
                ser.sensor_id,
                ses.sn AS sensor_sn,
                ses.name AS sensor_name,
                ser.last_entry_time,
                ser.tempareture AS original_temperature,
                ser.humidity AS original_humidity,
                CASE 
                    WHEN date_part('milliseconds', ser.last_entry_time) = 0 THEN ser.tempareture 
                    ELSE NULL 
                END AS zero_temp,
                CASE 
                    WHEN date_part('milliseconds', ser.last_entry_time) = 0 THEN ser.humidity 
                    ELSE NULL 
                END AS zero_hum,
                CASE 
                    WHEN date_part('milliseconds', ser.last_entry_time) = 0 THEN ser.last_entry_time 
                    ELSE NULL 
                END AS zero_ts
            FROM sensor_environmentsensorrecord ser
            JOIN sensor_environmentsensor ses ON ser.sensor_id = ses.id
            JOIN tent_tent t ON ses.tent_id = t.id
            WHERE t.company_id = 1
        ),
        numbered AS (
            SELECT *,
                COUNT(zero_temp) OVER (
                    PARTITION BY sensor_sn
                    ORDER BY last_entry_time
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS grp_temp,
                COUNT(zero_hum) OVER (
                    PARTITION BY sensor_sn
                    ORDER BY last_entry_time
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS grp_hum
            FROM base
        ),
        carried AS (
            SELECT *,
                MAX(zero_temp) OVER (
                    PARTITION BY sensor_sn, grp_temp
                    ORDER BY last_entry_time
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS last_zero_temp,
                MAX(zero_hum) OVER (
                    PARTITION BY sensor_sn, grp_hum
                    ORDER BY last_entry_time
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS last_zero_hum,
                MAX(zero_ts) OVER (
                    PARTITION BY sensor_sn, grp_temp
                    ORDER BY last_entry_time
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS last_zero_ts_temp,
                MAX(zero_ts) OVER (
                    PARTITION BY sensor_sn, grp_hum
                    ORDER BY last_entry_time
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS last_zero_ts_hum
            FROM numbered
        ),
        to_update AS (
            SELECT
                sensor_record_id,
                CASE 
                    WHEN date_part('milliseconds', last_entry_time) <> 0 
                        AND last_zero_temp IS NOT NULL 
                        AND EXTRACT(EPOCH FROM (last_entry_time - last_zero_ts_temp)) / 60 < 11
                    THEN last_zero_temp
                    ELSE NULL
                END AS new_temperature,
                CASE 
                    WHEN date_part('milliseconds', last_entry_time) <> 0 
                        AND last_zero_hum IS NOT NULL 
                        AND EXTRACT(EPOCH FROM (last_entry_time - last_zero_ts_hum)) / 60 < 11
                    THEN last_zero_hum
                    ELSE NULL
                END AS new_humidity
            FROM carried
            WHERE 
                (date_part('milliseconds', last_entry_time) <> 0)
                AND (
                    (last_zero_temp IS NOT NULL AND EXTRACT(EPOCH FROM (last_entry_time - last_zero_ts_temp)) / 60 < 11)
                    OR 
                    (last_zero_hum IS NOT NULL AND EXTRACT(EPOCH FROM (last_entry_time - last_zero_ts_hum)) / 60 < 11)
                )
        )
        UPDATE sensor_environmentsensorrecord ser
        SET
            tempareture = COALESCE(u.new_temperature, ser.tempareture),
            humidity = COALESCE(u.new_humidity, ser.humidity)
        FROM to_update u
        WHERE ser.id = u.sensor_record_id;
        """
        self.stdout.write("Running environment sensor correction SQL...")

        with connection.cursor() as cursor:
            cursor.execute(sql)

        self.stdout.write(self.style.SUCCESS("Sensor data updated successfully."))
