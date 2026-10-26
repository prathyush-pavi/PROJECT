# Database Schema Reference

DigitalGuard utilizes a relational schema optimized for high-volume telemetry ingestion and fast dashboard queries.

## Entities
1. **User**: Extends `AbstractUser`, handles authentication with `email` as username, role (`PARENT` or `ADMIN`).
2. **ParentProfile**: Linked 1:1 with `User`, stores display name and JSON alert preferences.
3. **ChildProfile**: Child profile details, avatar representation, linked to parent.
4. **Device**: Monitored hardware (Windows, Mobile, Tablet). Holds unique `device_token` (UUID) used for zero-cookie API authentication.
5. **WebsitePolicy**: URL/Domain rules (`BLOCK`, `WARN`, `ALLOW`), optional child scope.
6. **ApplicationPolicy**: Windows executable rules (`BLOCK`, `LIMITED`, `ALLOW`) with daily minute allotments.
7. **ScreenTimePolicy**: Daily screen time limits, weekend limits, and bedtime windows.
8. **ScreenTimeUsage**: Daily accumulated duration and JSON per-application breakdown.
9. **ActivityLog**: High-performance indexed stream of events (`timestamp`, `severity`, `event_type`, `domain`).
10. **ThreatEvent**: 1:1 linked with flagged `ActivityLog`, contains risk score, AI category, confidence, and indicators.
11. **Alert**: High-priority parent alerts with `is_read` status.
12. **Report**: Aggregated safety audits for scheduled parent reviews.
