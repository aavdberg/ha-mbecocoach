# Mercedes Eco Coach integration

- Target Home Assistant 2026.9 with a Config Flow and `DataUpdateCoordinator`.
- Work on `dev`; do not promote to `main` without an explicit release request.
- Never invent API endpoints or response fields. A redacted iOS 5.7.0 capture confirms `GET /api/v5/{VIN}/statistics/personal` returns nested cards (not flat numeric metrics), and also shows `/api/v5/{VIN}/report`, `/api/v5/{VIN}/statistics/all`, and `/api/v5/user/points`. The app's Eco Coach bearer token matches the access token from its OAuth refresh response; initial login and automated refresh remain unimplemented.
- Never commit or log actual tokens, VINs, captures, trip data, or private personal information. Use synthetic fixtures in tests.
- Add an English GitHub issue before each feature or bug fix, and validate with Ruff, pytest, hassfest and HACS workflows.
