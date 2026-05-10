Unit tests for service business logic with mocked repositories.

Inject mock repos via `app.dependency_overrides[get_x_service]` or construct services directly with stub repos. No DB connection needed. Focus on role checks, conflict detection, and decision branches — not SQL correctness (that belongs in integration tests).
