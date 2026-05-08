# core/

Application wiring: factory, registry, middleware, exception handlers, and dependencies.

Nothing in `core/` contains business logic. It assembles the FastAPI app and provides the infrastructure all other layers depend on.