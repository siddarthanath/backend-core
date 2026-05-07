# services/

Business logic layer. Takes Pydantic schemas in, calls repositories, returns Pydantic schemas out.

`sessions/` holds the `DatabaseSession` class. All other service files are domain-specific (e.g., `project_service.py`). Never construct API responses in repositories — that's the service's job.