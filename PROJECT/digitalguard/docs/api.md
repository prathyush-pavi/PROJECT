# REST API Reference

The DigitalGuard Backend exposes a RESTful API with two primary authentication schemes:
1. **Parent JWT Token**: `Authorization: Bearer <access_token>`
2. **Device Token**: `Authorization: DeviceToken <device_uuid>`

## Authentication Endpoints
- `POST /api/auth/register/`: Create parent account
- `POST /api/auth/login/`: Obtain JWT access and refresh token pair
- `POST /api/auth/logout/`: Revoke session
- `POST /api/auth/token/refresh/`: Refresh JWT token

## Monitoring & Telemetry (Device Token Auth)
- `POST /api/activity/ingest/`: Report browsing events, application violations, or threat detections
- `POST /api/screentime/ingest/`: Post daily screen time minutes and per-application breakdown
- `POST /api/browser/check-url/`: Query backend for domain policies and categorization

## Parental Control & Dashboard (JWT Bearer Auth)
- `GET /api/dashboard/summary/`: Retrieve high-level statistics for overview cards
- `GET /api/children/`: List or register children profiles
- `GET /api/devices/`: List or register monitored devices
- `GET /api/activity/`: Paginated and filterable activity stream
- `GET /api/alerts/`: Parental alert notifications
- `PATCH /api/alerts/<id>/mark-read/`: Mark alert resolved
- `GET / POST / DELETE /api/policies/websites/`: Website allow/block/warn policies
- `GET / POST / DELETE /api/policies/applications/`: Windows application policies
- `GET /api/screentime/usage/`: Historical screen time telemetry
- `GET /api/reports/`: Weekly and monthly safety summaries
