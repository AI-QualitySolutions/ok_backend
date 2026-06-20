import time as time_module
from datetime import datetime, timezone as dt_timezone

from django.http import QueryDict
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from camera.models import Camera, CameraHeartbeat, CounterHistory
from camera.serializers import CounterHistorySerializer
from camera.views import smart_aggregate
from utils.time import Current_saudi_time, convert_utc_to_riyadh, start_end_time_to_riyad
from django.utils.dateparse import parse_datetime
import pytz


_RIYADH_TZ = pytz.timezone("Asia/Riyadh")


@method_decorator(csrf_exempt, name='dispatch')
class CameraHeartbeatView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @staticmethod
    def _flatten_data(data):
        flat = data.copy() if isinstance(data, QueryDict) else dict(data)
        for key, value in flat.items():
            if isinstance(value, list) and len(value) == 1:
                flat[key] = value[0]
        return flat

    @staticmethod
    def _parse_unix_timestamp(val):
        """POSIX Unix seconds since 1970-01-01 00:00:00 UTC (not local wall)."""
        if val is None or val == '':
            return None, None
        if isinstance(val, str):
            val = val.strip()
            if val == '':
                return None, None
        try:
            ts = int(float(val))
        except (TypeError, ValueError):
            return None, None
        if ts > 1_000_000_000_000:  # milliseconds (> ~2001 as seconds)
            ts //= 1000
        try:
            return ts, datetime.fromtimestamp(ts, tz=dt_timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None, None

    def post(self, request, *args, **kwargs):
        data = self._flatten_data(request.data)
        sn = data.get('sn')

        ## CLEAN AFTER DEBUG ##
        print(f"data: {data}")
        print(f"sn: {sn}")
        ## CLEAN AFTER DEBUG ##

        if not sn:
            return Response({"code": 1, "msg": "sn is required"}, status=400)

        raw_time = data.get('time')
        if raw_time is None or raw_time == '':
            return Response({"code": 1, "msg": "time is required"}, status=400)

        unix_ts, heartbeat_time = self._parse_unix_timestamp(raw_time)
        if heartbeat_time is None:
            return Response({"code": 1, "msg": "time is invalid"}, status=400)

        try:
            camera = Camera.objects.get(sn=sn)
        except Camera.DoesNotExist:
            return Response({"code": 1, "msg": "sn non-existent"}, status=404)

        if camera.type != "peoplecount":
            return Response(
                {"code": 1, "msg": "camera is not a people counter"},
                status=400,
            )

        heartbeat, _ = CameraHeartbeat.objects.get_or_create(
            camera=camera,
            defaults={'sn': sn},
        )

        # Use QuerySet.update so `time` is always written in SQL. Some setups were
        # seeing updated_at move while `time` appeared stuck when using only save().
        patch = {
            'time': heartbeat_time,
            'sn': sn,
            'updated_at': timezone.now().astimezone(_RIYADH_TZ),
        }
        for field in (
            'version', 'mac_address', 'ip_address', 'connection_type',
            'ip_address_method', 'host_name', 'time_zone', 'hw_platform',
            'report_date', 'status_log',
        ):
            if field in data:
                patch[field] = data[field]
        CameraHeartbeat.objects.filter(pk=heartbeat.pk).update(**patch)

        return Response({
            "code": 0,
            "msg": "success",
            "data": {
                "sn": sn,
                "uploadInterval": 1,
                "dataMode": "Add",
                "time": unix_ts,
                "timezone": 6,
            }
        }, status=200)


#@method_decorator(csrf_exempt, name='dispatch')
class CounterHistoryView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, *args, **kwargs):
        sn = request.data.get('sn')

        if not sn:
            return Response({"code": 1, "msg": "sn is required"}, status=400)

        try:
            camera = Camera.objects.get(sn=sn)
        except Camera.DoesNotExist:
            return Response({"code": 1, "msg": "sn non-existent"}, status=404)

        def unix_to_dt(val):
            try:
                return datetime.fromtimestamp(int(val), tz=dt_timezone.utc)
            except (TypeError, ValueError):
                return None

        data = {
            'camera':         camera.id,
            'sn':             sn,
            'total_in':       request.data.get('in', 0),
            'total_out':      request.data.get('out', 0),
            'passby':         request.data.get('passby', 0),
            'turnback':       request.data.get('turnback', 0),
            'avg_stay_time':  request.data.get('avgStayTime', 0),
            'in_adult':       request.data.get('inAdult', 0),
            'out_adult':      request.data.get('outAdult', 0),
            'passby_adult':   request.data.get('passbyAdult', 0),
            'turnback_adult': request.data.get('turnbackAdult', 0),
            'in_child':       request.data.get('inChild', 0),
            'out_child':      request.data.get('outChild', 0),
            'passby_child':   request.data.get('passbyChild', 0),
            'turnback_child': request.data.get('turnbackChild', 0),
            'total':          request.data.get('total', 0),
            'start_time':     unix_to_dt(request.data.get('startTime')),
            'end_time':       unix_to_dt(request.data.get('endTime')),
        }

        serializer = CounterHistorySerializer(data=data, context={"request": request})

        if serializer.is_valid():
            counter_history = serializer.save()

            if camera.tent:
                difference = counter_history.total_in - counter_history.total_out
                camera.tent.staying += difference
                camera.tent.save()

            return Response({
                "code": 0,
                "msg": "success",
                "data": {
                    "sn": sn,
                    "time": int(time_module.time()),
                }
            }, status=200)

        return Response({
            "code": 2,
            "msg": "failed",
            "errors": serializer.errors
        }, status=400)


class TentCameraInfoView(APIView):
    """
    Returns every tent, the peoplecount cameras under it, and each
    camera's CounterHistory records for the current Saudi date.
    GET /api/camera/tentCameraInfo
    """

    def get(self, request):
        start_str = request.GET.get('start_date_time')
        end_str   = request.GET.get('end_date_time')
        tent_ids  = request.GET.get('tent_ids')

        start_dt = parse_datetime(start_str) if start_str else None
        end_dt   = parse_datetime(end_str)   if end_str   else None

        if start_dt and end_dt:
            day_start = start_end_time_to_riyad(start_dt)
            day_end   = start_end_time_to_riyad(end_dt)
        else:
            day_start, day_end = Current_saudi_time()

        # Query 1: all peoplecount cameras with their tent in one shot
        camera_filter = {"type": "peoplecount", "tent__isnull": False}

        if tent_ids:
            tent_id_list = [
                int(tid.strip())
                for tid in tent_ids.split(',')
                if tid.strip().isdigit()
            ]
            if not tent_id_list:
                return Response({"error": "Invalid tent_ids format. Use comma-separated integers."}, status=400)
            camera_filter["tent_id__in"] = tent_id_list

        cameras = (
            Camera.objects
            .filter(**camera_filter)
            .select_related('tent')
            .order_by('tent_id', 'id')
        )

        # Query 2: all CounterHistory rows for those cameras in the date range
        all_records = (
            CounterHistory.objects
            .filter(
                camera__in=cameras,
                created_at__gte=day_start,
                created_at__lte=day_end,
            )
            .only('id', 'camera_id', 'total_in', 'total_out',
                  'created_at', 'start_time', 'end_time')
            .order_by('camera_id', 'created_at')
        )

        from collections import defaultdict
        from datetime import timedelta

        BUCKET_SIZE     = timedelta(minutes=5)
        BUCKET_SECS     = int(BUCKET_SIZE.total_seconds())

        # O(1) lookup: camera_id → camera object
        cam_lookup = {c.id: c for c in cameras}

        # Build tent → {cameras, bucket_map} structure
        # bucket_map: bucket_idx → {camera_id → {meta, records}}
        tents_map = {}
        for cam in cam_lookup.values():
            tid = cam.tent_id
            if tid not in tents_map:
                tents_map[tid] = {
                    "tent_id":    cam.tent.id,
                    "tent_name":  cam.tent.name,
                    "camera_sns": [],
                    "bucket_map": defaultdict(dict),
                }
            tents_map[tid]["camera_sns"].append({"camera_id": cam.id, "sn": cam.sn})

        # Place every record into tent → bucket → camera slot
        for rec in all_records:
            if not rec.created_at:
                continue
            cam_obj = cam_lookup.get(rec.camera_id)
            if not cam_obj:
                continue
            tid        = cam_obj.tent_id
            delta_secs = (rec.created_at - day_start).total_seconds()
            bucket_idx = int(delta_secs // BUCKET_SECS)

            tent_buckets = tents_map[tid]["bucket_map"]
            if rec.camera_id not in tent_buckets[bucket_idx]:
                tent_buckets[bucket_idx][rec.camera_id] = {
                    "camera_id": cam_obj.id,
                    "sn":        cam_obj.sn,
                    "records":   [],
                }
            tent_buckets[bucket_idx][rec.camera_id]["records"].append(rec)

        # Serialise into final output
        def fmt_rec(r):
            return {
                "id":         r.id,
                "total_in":   r.total_in,
                "total_out":  r.total_out,
                "created_at": convert_utc_to_riyadh(r.created_at).isoformat() if r.created_at else None,
                "start_time": convert_utc_to_riyadh(r.start_time).isoformat() if r.start_time else None,
                "end_time":   convert_utc_to_riyadh(r.end_time).isoformat()   if r.end_time   else None,
            }

        result = []
        for tent_data in tents_map.values():
            running_in  = 0
            running_out = 0
            buckets     = []

            for idx in sorted(tent_data["bucket_map"].keys()):
                b_start     = day_start + idx * BUCKET_SIZE
                b_end       = b_start + BUCKET_SIZE
                cam_slots   = tent_data["bucket_map"][idx]

                # Per-camera sums for this bucket
                cam_in_values  = [sum(r.total_in  for r in slot["records"]) for slot in cam_slots.values()]
                cam_out_values = [sum(r.total_out for r in slot["records"]) for slot in cam_slots.values()]

                # Closest-pair average of the two nearest cameras; falls back
                # to the highest value when two cameras report 0.
                b_in  = smart_aggregate(cam_in_values)
                b_out = smart_aggregate(cam_out_values)

                buckets.append({
                    "bucket_start":     b_start.isoformat(),
                    "bucket_end":       b_end.isoformat(),
                    "total_in_before":  running_in,
                    "total_out_before": running_out,
                    "bucket_total_in":  b_in,
                    "bucket_total_out": b_out,
                    "cameras": [
                        {
                            "camera_id":        slot["camera_id"],
                            "sn":               slot["sn"],
                            "camera_total_in":  sum(r.total_in  for r in slot["records"]),
                            "camera_total_out": sum(r.total_out for r in slot["records"]),
                            "records":          [fmt_rec(r) for r in slot["records"]],
                        }
                        for slot in cam_slots.values()
                    ],
                })

                running_in  += b_in
                running_out += b_out

            result.append({
                "tent_id":      tent_data["tent_id"],
                "tent_name":    tent_data["tent_name"],
                "camera_sns":   tent_data["camera_sns"],
                "bucket_count": len(buckets),
                "buckets":      buckets,
            })

        return Response({
            "date_range": {
                "start": convert_utc_to_riyadh(day_start).isoformat(),
                "end":   convert_utc_to_riyadh(day_end).isoformat(),
            },
            "tents": result,
        })
