# API Documentation — AI Camera Data Ingestion Endpoints

**Base URL:** `https://backend.aihajjservices.com`  
**Content-Type:** `multipart/form-data` (all endpoints accept file uploads)  
**Authentication:** Each endpoint requires a secret key passed in the request header.

---

## Common Rules

- All endpoints use **POST** method.
- The `sn` field is the **Camera Serial Number** — must match a camera registered in the system.
- `start_time` and `end_time` must be in **ISO 8601** format: `YYYY-MM-DDTHH:MM:SS`
- `image` is always optional but recommended.
- A wrong or missing secret key returns **403 Forbidden**.
- A camera SN not found in the system returns **404 Not Found**.

---

## 1. Guard Presence

**Endpoint:** `POST /camera/create-guard-detect/`  
**Secret Key Header:** `X-Secret-Key: e5oNH8Yhx8eJml4bSxYw`

### Fields

| Field         | Type     | Mandatory | Description                          |
|---------------|----------|-----------|--------------------------------------|
| `sn`          | string   | Yes       | Camera serial number                 |
| `guard_count` | integer  | Yes       | Number of guards detected (0 = none) |
| `present`     | boolean  | Yes       | `true` if guard is present           |
| `start_time`  | datetime | Yes       | Interval start time                  |
| `end_time`    | datetime | Yes       | Interval end time                    |
| `image`       | file     | No        | Snapshot image                       |

### Example Request (curl)

```bash
curl -X POST https://backend.aihajjservices.com/camera/create-guard-detect/ \
  -H "X-Secret-Key: e5oNH8Yhx8eJml4bSxYw" \
  -F "sn=CAM-001" \
  -F "guard_count=2" \
  -F "present=true" \
  -F "start_time=2026-05-04T10:00:00" \
  -F "end_time=2026-05-04T10:15:00" \
  -F "image=@/path/to/snapshot.jpg"
```

### Success Response (201 Created)

```json
{
  "message": "Guard Presence History created successfully."
}
```

---

## 2. Kitchen Violation

**Endpoint:** `POST /camera/create-kitchen-violation-report/`  
**Secret Key Header:** `X-Secret-Key: e5oNH8Yhx8eJml4bSxYw`

### Fields

| Field            | Type     | Mandatory | Description                                          |
|------------------|----------|-----------|------------------------------------------------------|
| `sn`             | string   | Yes       | Camera serial number                                 |
| `violation`      | boolean  | Yes       | `true` if a violation was detected                   |
| `violation_list` | JSON     | Yes       | List of violations e.g. `["no_hat", "no_gloves"]`   |
| `start_time`     | datetime | Yes       | Interval start time                                  |
| `end_time`       | datetime | Yes       | Interval end time                                    |
| `image`          | file     | No        | Snapshot image                                       |

### Example Request (curl)

```bash
curl -X POST https://backend.aihajjservices.com/camera/create-kitchen-violation-report/ \
  -H "X-Secret-Key: e5oNH8Yhx8eJml4bSxYw" \
  -F "sn=CAM-002" \
  -F "violation=true" \
  -F 'violation_list=["no_hat","no_gloves"]' \
  -F "start_time=2026-05-04T08:00:00" \
  -F "end_time=2026-05-04T08:15:00" \
  -F "image=@/path/to/snapshot.jpg"
```

### Success Response (201 Created)

```json
{
  "message": "Violation report created successfully.",
  "data": { ... }
}
```

---

## 3. Buffet Violation

**Endpoint:** `POST /camera/create-buffet-violation/`  
**Secret Key Header:** `X-Secret-Key: e5oNH8Yhx8eJml4bSxYw`

### Fields

| Field            | Type     | Mandatory | Description                                              |
|------------------|----------|-----------|----------------------------------------------------------|
| `sn`             | string   | Yes       | Camera serial number                                     |
| `violation`      | boolean  | Yes       | `true` if a violation was detected                       |
| `violation_list` | JSON     | Yes       | List of violations e.g. `["no_mask", "improper_dress"]`  |
| `start_time`     | datetime | Yes       | Interval start time                                      |
| `end_time`       | datetime | Yes       | Interval end time                                        |
| `image`          | file     | No        | Snapshot image                                           |

### Example Request (curl)

```bash
curl -X POST https://backend.aihajjservices.com/camera/create-buffet-violation/ \
  -H "X-Secret-Key: e5oNH8Yhx8eJml4bSxYw" \
  -F "sn=CAM-003" \
  -F "violation=true" \
  -F 'violation_list=["no_mask"]' \
  -F "start_time=2026-05-04T12:00:00" \
  -F "end_time=2026-05-04T12:15:00" \
  -F "image=@/path/to/snapshot.jpg"
```

### Success Response (201 Created)

```json
{
  "message": "Violation report created successfully.",
  "data": { ... }
}
```

---

## 4. Clean (Cleaners Presence)

**Endpoint:** `POST /camera/create-cleaners-presence/`  
**Secret Key Header:** `X-Secret-Key: e5oNH8Yhx8eJml4bSxYw`

### Fields

| Field           | Type     | Mandatory | Description                             |
|-----------------|----------|-----------|-----------------------------------------|
| `sn`            | string   | Yes       | Camera serial number                    |
| `cleaner_count` | integer  | Yes       | Number of cleaners detected (0 = none)  |
| `present`       | boolean  | Yes       | `true` if a cleaner is present          |
| `start_time`    | datetime | Yes       | Interval start time                     |
| `end_time`      | datetime | Yes       | Interval end time                       |
| `image`         | file     | No        | Snapshot image                          |

### Example Request (curl)

```bash
curl -X POST https://backend.aihajjservices.com/camera/create-cleaners-presence/ \
  -H "X-Secret-Key: e5oNH8Yhx8eJml4bSxYw" \
  -F "sn=CAM-004" \
  -F "cleaner_count=1" \
  -F "present=true" \
  -F "start_time=2026-05-04T09:00:00" \
  -F "end_time=2026-05-04T09:15:00" \
  -F "image=@/path/to/snapshot.jpg"
```

### Success Response (201 Created)

```json
{
  "message": "Cleaners Presence History created successfully."
}
```

---

## 5. Garbage Monitoring

**Endpoint:** `POST /camera/create-garbage-monitoring/`  
**Secret Key Header:** `X-Secret-Key: e5oNH8Yhx8eJml4bSxYw`

### Fields

| Field        | Type     | Mandatory | Description                               |
|--------------|----------|-----------|-------------------------------------------|
| `sn`         | string   | Yes       | Camera serial number                      |
| `is_clean`   | boolean  | Yes       | `true` = area is clean, `false` = garbage |
| `start_time` | datetime | Yes       | Interval start time                       |
| `end_time`   | datetime | Yes       | Interval end time                         |
| `image`      | file     | No        | Snapshot image                            |

### Example Request (curl)

```bash
curl -X POST https://backend.aihajjservices.com/camera/create-garbage-monitoring/ \
  -H "X-Secret-Key: e5oNH8Yhx8eJml4bSxYw" \
  -F "sn=CAM-005" \
  -F "is_clean=false" \
  -F "start_time=2026-05-04T07:00:00" \
  -F "end_time=2026-05-04T07:15:00" \
  -F "image=@/path/to/snapshot.jpg"
```

### Success Response (201 Created)

```json
{
  "message": "Garbage Monitoring History created successfully.",
  "data": { ... }
}
```

---

## 5b. Recycle Monitoring

**Endpoint:** `POST /camera/create-recycle-monitoring/`  
**Secret Key Header:** `X-Secret-Key: <RECYCLE_DETECTION_KEY>`

### Fields

| Field            | Type     | Mandatory | Description                                         |
|------------------|----------|-----------|-----------------------------------------------------|
| `sn`             | string   | Yes       | Camera serial number                                |
| `is_clean`       | boolean  | Yes       | `true` = area is clean, `false` = recycle detected  |
| `start_time`     | datetime | Yes       | Interval start time (ISO 8601)                      |
| `end_time`       | datetime | Yes       | Interval end time (ISO 8601)                        |
| `current_status` | JSON     | No        | Current detection status e.g. `["recycle"]`         |
| `image`          | file     | No        | Snapshot image                                      |

### Example Request (curl)

```bash
curl -X POST https://backend.aihajjservices.com/camera/create-recycle-monitoring/ \
  -H "X-Secret-Key: <RECYCLE_DETECTION_KEY>" \
  -F "sn=CAM-005" \
  -F "is_clean=false" \
  -F 'current_status=["recycle"]' \
  -F "start_time=2026-05-04T07:00:00" \
  -F "end_time=2026-05-04T07:15:00" \
  -F "image=@/path/to/snapshot.jpg"
```

### Success Response (201 Created)

```json
{
  "message": "Recycle Monitoring History created successfully.",
  "data": {
    "id": 1,
    "camera": 5,
    "is_clean": false,
    "current_status": ["recycle"],
    "annotator_status": "",
    "ai_status": null,
    "start_time": "2026-05-04T07:00:00Z",
    "end_time": "2026-05-04T07:15:00Z",
    "image": "/media/recycle_monitoring_history/2026/05/04/snapshot.jpg",
    "created_at": "2026-05-04T07:16:00Z",
    "updated_at": "2026-05-04T07:16:00Z",
    "camera_type": "recycle",
    "is_annotated": false,
    "tent_name": "Tent A",
    "camera_sn": "CAM-005",
    "is_rejected": false,
    "is_ai_annotated": false,
    "ai_annotation_time": null,
    "time": "2026-05-04T07:16:00Z"
  }
}
```

---

## 6. Sentiment Analysis

**Endpoint:** `POST /camera/create-sentiment-analysis/`  
**Secret Key Header:** `X-Secret-Key: e5oNH8Yhx8eJml4bSxYw`

### Fields

| Field               | Type     | Mandatory | Description                                              |
|---------------------|----------|-----------|----------------------------------------------------------|
| `sn`                | string   | Yes       | Camera serial number                                     |
| `sentiment_list`    | JSON     | Yes       | List of detected sentiments e.g. `["happy", "neutral"]` |
| `average_sentiment` | float    | Yes       | Average sentiment score                                  |
| `start_time`        | datetime | Yes       | Interval start time                                      |
| `end_time`          | datetime | Yes       | Interval end time                                        |
| `report_date`       | date     | No        | Date of report `YYYY-MM-DD`                              |
| `version`           | integer  | No        | Device firmware version                                  |
| `mac_address`       | string   | No        | Device MAC address                                       |
| `ip_address`        | string   | No        | Device IP address                                        |
| `connection_type`   | string   | No        | e.g. `wifi`, `ethernet`                                  |
| `ip_address_method` | string   | No        | e.g. `dhcp`, `static`                                    |
| `host_name`         | string   | No        | Device hostname                                          |
| `time_zone`         | integer  | No        | Timezone offset in hours                                 |
| `hw_platform`       | string   | No        | Hardware platform name                                   |
| `image`             | file     | No        | Snapshot image                                           |

### Example Request (curl)

```bash
curl -X POST https://backend.aihajjservices.com/camera/create-sentiment-analysis/ \
  -H "X-Secret-Key: e5oNH8Yhx8eJml4bSxYw" \
  -F "sn=CAM-006" \
  -F 'sentiment_list=["happy","neutral"]' \
  -F "average_sentiment=0.75" \
  -F "start_time=2026-05-04T11:00:00" \
  -F "end_time=2026-05-04T11:15:00" \
  -F "report_date=2026-05-04" \
  -F "mac_address=AA:BB:CC:DD:EE:FF" \
  -F "ip_address=192.168.1.50" \
  -F "image=@/path/to/snapshot.jpg"
```

### Success Response (201 Created)

```json
{
  "message": "Sentiment analysis report created successfully.",
  "data": { ... }
}
```

---

## 7. Crowd Monitoring

**Endpoint:** `POST /camera/create-crowd-monitoring/`  
**Secret Key Header:** `X-Secret-Key: <GARBAGE_DETECTION_KEY>`

### Fields

| Field        | Type     | Mandatory | Description                                      |
|--------------|----------|-----------|--------------------------------------------------|
| `sn`         | string   | Yes       | Camera serial number                             |
| `crowd`      | string   | No        | Crowd density level — `"high"` or `"warn"` (omit to leave status unset) |
| `start_time` | datetime | Yes       | Interval start time (ISO 8601)                   |
| `end_time`   | datetime | Yes       | Interval end time (ISO 8601)                     |
| `image`      | file     | No        | Snapshot image                                   |

> `"high"` sets `is_crowd = true`. `"warn"` sets `is_crowd = false`. Omitting `crowd` entirely is allowed — `is_crowd` defaults to `false`. Sending any other non-empty value returns **400**.

### Example Request (curl)

```bash
curl -X POST https://backend.aihajjservices.com/camera/create-crowd-monitoring/ \
  -H "X-Secret-Key: e5oNH8Yhx8eJml4bSxYw" \
  -F "sn=CAM-007" \
  -F "crowd=high" \
  -F "start_time=2026-05-04T14:00:00" \
  -F "end_time=2026-05-04T14:15:00" \
  -F "image=@/path/to/snapshot.jpg"
```

### Success Response (201 Created)

```json
{
  "message": "Crowd Monitoring History created successfully.",
  "data": {
    "id": 42,
    "is_crowd": true,
    "current_status": ["high"],
    "start_time": "2026-05-04T14:00:00",
    "end_time": "2026-05-04T14:15:00"
  }
}
```

---

## 8. Counter Camera — Heartbeat

**Endpoint:** `POST /api/camera/heartBeat`  
**Authentication:** None (device-to-server push)

### Fields

| Field               | Type    | Mandatory | Description                            |
|---------------------|---------|-----------|----------------------------------------|
| `sn`                | string  | Yes       | Camera serial number                   |
| `version`           | string  | No        | Firmware version                       |
| `mac_address`       | string  | No        | Device MAC address                     |
| `ip_address`        | string  | No        | Device IP address                      |
| `connection_type`   | string  | No        | e.g. `wifi`, `ethernet`                |
| `ip_address_method` | string  | No        | e.g. `dhcp`, `static`                 |
| `host_name`         | string  | No        | Device hostname                        |
| `time_zone`         | integer | No        | Timezone offset in hours               |
| `hw_platform`       | string  | No        | Hardware platform name                 |
| `report_date`       | date    | No        | Report date `YYYY-MM-DD`               |
| `status_log`        | string  | No        | Device status log text                 |

### Example Request (curl)

```bash
curl -X POST https://backend.aihajjservices.com/api/camera/heartBeat \
  -F "sn=CAM-COUNTER-001" \
  -F "version=1.2.3" \
  -F "mac_address=AA:BB:CC:DD:EE:FF" \
  -F "ip_address=192.168.1.55" \
  -F "connection_type=wifi" \
  -F "report_date=2026-05-04"
```

### Success Response (200 OK)

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "sn": "CAM-COUNTER-001",
    "uploadInterval": 1,
    "dataMode": "Add",
    "time": 1746355200,
    "timezone": 6
  }
}
```

---

## 9. Counter Camera — Data Upload

**Endpoint:** `POST /api/camera/dataUpload`  
**Authentication:** None (device-to-server push)

### Fields

| Field           | Type    | Mandatory | Description                              |
|-----------------|---------|-----------|------------------------------------------|
| `sn`            | string  | Yes       | Camera serial number (must already exist)|
| `in`            | integer | No        | Total people entered                     |
| `out`           | integer | No        | Total people exited                      |
| `passby`        | integer | No        | People who passed by                     |
| `turnback`      | integer | No        | People who turned back                   |
| `avgStayTime`   | integer | No        | Average stay time (seconds)              |
| `inAdult`       | integer | No        | Adults entered                           |
| `outAdult`      | integer | No        | Adults exited                            |
| `passbyAdult`   | integer | No        | Adults who passed by                     |
| `turnbackAdult` | integer | No        | Adults who turned back                   |
| `inChild`       | integer | No        | Children entered                         |
| `outChild`      | integer | No        | Children exited                          |
| `passbyChild`   | integer | No        | Children who passed by                   |
| `turnbackChild` | integer | No        | Children who turned back                 |
| `total`         | integer | No        | Raw total (overridden by `in - out`)     |
| `startTime`     | integer | No        | Unix timestamp — interval start          |
| `endTime`       | integer | No        | Unix timestamp — interval end            |

> `total` is always recalculated as `in - out` on save.

### Example Request (curl)

```bash
curl -X POST https://backend.aihajjservices.com/api/camera/dataUpload \
  -F "sn=CAM-COUNTER-001" \
  -F "in=120" \
  -F "out=95" \
  -F "passby=30" \
  -F "turnback=5" \
  -F "avgStayTime=300" \
  -F "inAdult=100" \
  -F "outAdult=80" \
  -F "inChild=20" \
  -F "outChild=15" \
  -F "startTime=1746352800" \
  -F "endTime=1746354600"
```

### Success Response (200 OK)

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "sn": "CAM-COUNTER-001",
    "time": 1746355200
  }
}
```

### Error — SN not found (404)

```json
{
  "code": 1,
  "msg": "sn non-existent"
}
```

---

## Error Responses

| Status | Meaning                              |
|--------|--------------------------------------|
| 400    | Missing required field or bad data   |
| 403    | Wrong or missing `X-Secret-Key`      |
| 404    | Camera SN not found in system        |
| 500    | Unexpected server error              |

### Example Error (403)

```json
{
  "message": "Invalid X-Secret-Key.",
  "details": "Invalid guard detection secret key."
}
```

### Example Error (404)

```json
{
  "message": "Camera with SN 'CAM-999' does not exist."
}
```

---

## 7. Access Point (Router Heartbeat)

**Endpoint:** `POST /api/access-point/router-heartbeat/`  
**Secret Key Header:** `X-Secret-Key-Router: q9AsaZINIU4`

### Fields

| Field          | Type     | Mandatory | Description                        |
|----------------|----------|-----------|------------------------------------|
| `SN`           | string   | Yes       | Router serial number               |
| `ip_address`   | string   | Yes       | Must be a valid IPv4 or IPv6       |
| `heartbeat_time` | datetime | Yes     | ISO 8601 format                    |
| `mac_address`  | string   | No        | Router MAC address                 |

### Example Request (curl)

```bash
curl -X POST https://backend.aihajjservices.com/api/access-point/router-heartbeat/ \
  -H "Content-Type: application/json" \
  -H "X-Secret-Key-Router: q9AsaZINIU4" \
  -d '{
    "SN": "ROUTER-001",
    "ip_address": "192.168.1.100",
    "heartbeat_time": "2026-05-04T10:30:00+03:00",
    "mac_address": "AA:BB:CC:DD:EE:FF"
  }'
```

### Success Response (201 Created)

```json
{
  "message": "Heartbeat saved successfully",
  "SN": "ROUTER-001",
  "new_router_created": true
}
```

> `new_router_created` is `true` the first time a router SN is seen, `false` on subsequent heartbeats.

---

## Quick Reference Table

| Model              | Endpoint                                   | Secret Key Header     | Auth Value              |
|--------------------|--------------------------------------------|-----------------------|-------------------------|
| Guard              | `/camera/create-guard-detect/`             | `X-Secret-Key`        | `e5oNH8Yhx8eJml4bSxYw`  |
| Kitchen            | `/camera/create-kitchen-violation-report/` | `X-Secret-Key`        | `e5oNH8Yhx8eJml4bSxYw`  |
| Buffet             | `/camera/create-buffet-violation/`         | `X-Secret-Key`        | `e5oNH8Yhx8eJml4bSxYw`  |
| Clean              | `/camera/create-cleaners-presence/`        | `X-Secret-Key`        | `e5oNH8Yhx8eJml4bSxYw`  |
| Garbage            | `/camera/create-garbage-monitoring/`       | `X-Secret-Key`        | `e5oNH8Yhx8eJml4bSxYw`  |
| Recycle            | `/camera/create-recycle-monitoring/`         | `X-Secret-Key`        | `RECYCLE_DETECTION_KEY` |
| Sentiment          | `/camera/create-sentiment-analysis/`       | `X-Secret-Key`        | `e5oNH8Yhx8eJml4bSxYw`  |
| Access Point       | `/api/access-point/router-heartbeat/`      | `X-Secret-Key-Router` | `q9AsaZINIU4`           |
| Crowd Monitoring   | `/camera/create-crowd-monitoring/`         | `X-Secret-Key`        | `GARBAGE_DETECTION_KEY` |
| Counter Heartbeat  | `/api/camera/heartBeat`                    | None                  | —                       |
| Counter Data       | `/api/camera/dataUpload`                   | None                  | —                       |
