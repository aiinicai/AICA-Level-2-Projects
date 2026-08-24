# Initial Non-Functional Targets

These are Phase 0 design targets, to be validated with representative data and revised by ADR when evidence changes.

| Area | Initial target |
|---|---|
| Supported workload | 2,000 clients, 100 concurrent staff accounts, at least 5 million historical tasks without redesign |
| Interactive API | p95 under 2 seconds for paginated lists and ordinary commands on the LAN |
| Calendar/dashboard | p95 under 3 seconds for a bounded month/team view |
| Projection | under 5 seconds for one financial year at 2,000-client scale; larger exports asynchronous |
| Availability | Business-hours single-node service with automatic process restart; no false high-availability claim |
| Recovery | Provisional RPO 24 hours and RTO 4 hours until business owner confirms |
| Accessibility | Keyboard-operable workflows, visible focus, semantic labels, contrast not dependent on color alone |
| Security | TLS on LAN, server-side authorization, secure cookie sessions, no secrets in source/logs |
| Browser | Current managed Chrome/Edge; responsive down to tablet width; mobile app is out of MVP |
| Data retention | Transaction/audit retention provisional minimum seven financial years plus current year, subject to legal confirmation |

Every performance claim must state dataset size, filter, environment and percentile. Do not optimize by removing authorization or integrity checks.

