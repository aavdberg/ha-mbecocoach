# Mercedes Eco Coach integration

- Target Home Assistant 2026.9 with a Config Flow and `DataUpdateCoordinator`.
- Work on `dev`; do not promote to `main` without an explicit release request.
- Never invent API endpoints or response fields. Only `GET /api/v5/{VIN}/statistics/personal` and its three numeric metrics are observed so far; even their production reachability and token compatibility remain unverified.
- Never commit or log actual tokens, VINs, captures, trip data, or private personal information. Use synthetic fixtures in tests.
- Add an English GitHub issue before each feature or bug fix, and validate with Ruff, pytest, hassfest and HACS workflows.
