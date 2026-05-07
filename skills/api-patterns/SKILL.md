# API Patterns Skill

## Handler Template

Every handler follows this exact structure — thin, no business logic:

```python
@router.post("/thing", response_model=ThingResponse, status_code=201)
async def create_thing(
    body: CreateThingRequest,
    db: AsyncSession = Depends(get_db),
    user: UserClaims = Depends(get_current_user),
) -> ThingResponse:
    """One-line summary."""
    return await thing_service.create(db=db, user_id=user.sub, data=body)
```

Rules:
- `response_model=XResponse` on **every** endpoint — no `dict`, no `Any`, no raw SQLModel.
- Return type annotation must match `response_model`.
- No business logic in handlers. If you're writing an `if` that isn't about routing, it belongs in the service.
- Public endpoints omit `user: UserClaims = Depends(get_current_user)`.

## Request / Response Schemas

```python
# schemas/thing.py
class CreateThingRequest(BaseModel):
    name: str
    description: str | None = None

class ThingResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

`from_attributes=True` lets you call `ThingResponse.model_validate(orm_obj)` in the service layer.

## Error Responses

Never raise `HTTPException` directly. Raise typed exceptions from `src.core.exceptions`:

```python
from src.core.exceptions import NotFoundError, AuthException, ValidationError

raise NotFoundError(message="Project not found", detail=f"id={project_id}")
raise AuthException(message="You do not own this resource")
raise ValidationError(message="Name too long", detail="Max 100 characters")
```

All exceptions map to `ErrorEnvelope` via the handlers registered in `factory.py`.

## Router Registration

Add each new domain to `src/api/router.py`:

```python
from src.api.v1 import health, thing

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(thing.router)
```

Each domain file defines its own `router = APIRouter(tags=["thing"])`.

## Rate Limiting Per-Route

Global default is 60 req/min. Override for expensive endpoints:

```python
from src.core.middleware.rate_limit import limiter

@router.post("/generate", response_model=GenerateResponse)
@limiter.limit("10/minute")
async def generate(request: Request, ...) -> GenerateResponse:
    ...
```

`request: Request` must be the first parameter when using `@limiter.limit`.

## Data Flow (Never Skip a Layer)

```
HTTP Request
  → Pydantic schema (FastAPI validates)
  → Handler
  → Service (business logic, takes Pydantic in)
  → Repository (DB query, returns SQLModel)
  → Service converts: XResponse.model_validate(orm_obj)
  → Handler returns Pydantic response
  → HTTP Response (FastAPI serialises via response_model)
```