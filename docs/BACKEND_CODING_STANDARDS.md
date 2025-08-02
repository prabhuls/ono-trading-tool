# Backend Coding Standards

This document outlines the coding standards and best practices for the FastAPI backend of the Trading Tools platform.

## Table of Contents
- [Python Code Style](#python-code-style)
- [Project Structure](#project-structure)
- [API Design Standards](#api-design-standards)
- [Database Standards](#database-standards)
- [Service Layer Standards](#service-layer-standards)
- [Error Handling](#error-handling)
- [Testing Standards](#testing-standards)
- [Documentation Standards](#documentation-standards)
- [Security Standards](#security-standards)
- [Performance Guidelines](#performance-guidelines)

## Python Code Style

### General Guidelines

1. **Follow PEP 8** with the following modifications:
   - Line length: 88 characters (Black default)
   - Use double quotes for strings

2. **Use Black** for automatic formatting:
   ```bash
   black app/ --line-length 88
   ```

3. **Use Ruff** for linting:
   ```bash
   ruff check app/
   ```

### Function Design Principles

1. **Single Responsibility Principle (SRP)**:
   ```python
   # Bad - Function doing multiple things
   async def process_user_order(user_id: str, order_data: dict):
       # Validate user
       user = await get_user(user_id)
       if not user.is_active:
           raise ValueError("User not active")
       
       # Calculate pricing
       total = 0
       for item in order_data["items"]:
           price = await get_item_price(item["id"])
           total += price * item["quantity"]
       
       # Apply discounts
       if user.is_premium:
           total *= 0.9
       
       # Create order
       order = await create_order(user_id, order_data, total)
       
       # Send email
       await send_order_confirmation(user.email, order)
       
       return order
   
   # Good - Each function has a single responsibility
   async def validate_user_for_order(user_id: str) -> User:
       user = await get_user(user_id)
       if not user.is_active:
           raise ValueError("User not active")
       return user
   
   async def calculate_order_total(items: List[OrderItem], user: User) -> Decimal:
       total = await calculate_base_total(items)
       return apply_user_discounts(total, user)
   
   async def process_user_order(user_id: str, order_data: dict):
       user = await validate_user_for_order(user_id)
       total = await calculate_order_total(order_data["items"], user)
       order = await create_order(user_id, order_data, total)
       await send_order_confirmation(user.email, order)
       return order
   ```

2. **Keep functions small** (max 20-30 lines):
   ```python
   # Bad - Function too long
   async def process_payment(payment_data: PaymentData):
       # 50+ lines of code...
   
   # Good - Break into smaller functions
   async def process_payment(payment_data: PaymentData) -> PaymentResult:
       await validate_payment_data(payment_data)
       payment_method = await get_payment_method(payment_data.method_id)
       
       charge_result = await charge_payment_method(
           payment_method,
           payment_data.amount
       )
       
       if charge_result.success:
           return await finalize_payment(charge_result)
       else:
           return await handle_payment_failure(charge_result)
   ```

3. **File length limit** (max 300-500 lines):
   - If a file exceeds 300 lines, consider splitting into multiple modules
   - Group related functionality into separate files
   - Use `__init__.py` to maintain clean imports

### Type Hints

Always use type hints for function arguments and return values:

```python
# Good
async def get_user(user_id: str, db: AsyncSession) -> Optional[User]:
    return await db.get(User, user_id)

# Bad
async def get_user(user_id, db):
    return await db.get(User, user_id)
```

### Async/Await Patterns

1. **Always use async/await** for I/O operations:
   ```python
   # Good
   async def fetch_data():
       async with httpx.AsyncClient() as client:
           response = await client.get("https://api.example.com")
           return response.json()
   
   # Bad
   def fetch_data():
       response = requests.get("https://api.example.com")
       return response.json()
   ```

2. **Use asyncio.gather** for concurrent operations:
   ```python
   # Good
   results = await asyncio.gather(
       fetch_user_data(user_id),
       fetch_portfolio_data(user_id),
       fetch_watchlist_data(user_id)
   )
   ```

### Import Organization

Organize imports in the following order:
1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Standard library
import asyncio
from datetime import datetime
from typing import List, Optional

# Third-party
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse
```

## Project Structure

### Directory Organization

```
app/
├── api/              # API endpoints
│   └── v1/          # API versioning
│       ├── __init__.py
│       └── endpoints/
│           ├── __init__.py
│           ├── users.py
│           └── trading.py
├── core/            # Core functionality
│   ├── __init__.py
│   ├── config.py    # Settings management
│   ├── database.py  # Database connection
│   ├── logging.py   # Logging configuration
│   ├── cache.py     # Cache utilities
│   └── responses.py # Response formatting
├── models/          # SQLAlchemy models
│   ├── __init__.py
│   ├── user.py
│   └── base.py
├── schemas/         # Pydantic schemas
│   ├── __init__.py
│   └── user.py
├── services/        # Business logic
│   ├── __init__.py
│   └── external/
├── utils/           # Utility functions
└── main.py         # Application entry point
```

### Naming Conventions

1. **Files**: Use snake_case
   ```
   user_service.py
   api_client.py
   ```

2. **Classes**: Use PascalCase
   ```python
   class UserService:
       pass
   
   class APIKeyManager:
       pass
   ```

3. **Functions/Variables**: Use snake_case
   ```python
   def calculate_portfolio_value():
       pass
   
   user_count = 100
   ```

4. **Constants**: Use UPPER_SNAKE_CASE
   ```python
   MAX_RETRY_ATTEMPTS = 3
   DEFAULT_PAGE_SIZE = 50
   ```

## API Design Standards

### RESTful Conventions

1. **Use proper HTTP methods**:
   - GET: Retrieve resources
   - POST: Create new resources
   - PUT: Full update of resources
   - PATCH: Partial update of resources
   - DELETE: Remove resources

2. **Endpoint naming**:
   ```python
   # Good
   @router.get("/users")          # List users
   @router.get("/users/{id}")     # Get specific user
   @router.post("/users")         # Create user
   @router.patch("/users/{id}")   # Update user
   @router.delete("/users/{id}")  # Delete user
   
   # Bad
   @router.get("/get-users")
   @router.post("/create-user")
   ```

3. **Use plural nouns** for resource names:
   ```
   /api/v1/users (not /api/v1/user)
   /api/v1/portfolios (not /api/v1/portfolio)
   ```

### Request/Response Schemas

1. **Always use Pydantic models**:
   ```python
   # schemas/user.py
   class UserCreate(BaseModel):
       email: EmailStr
       username: str = Field(..., min_length=3, max_length=50)
       password: str = Field(..., min_length=8)
   
   class UserResponse(BaseModel):
       id: str
       email: str
       username: str
       created_at: datetime
       
       class Config:
           orm_mode = True
   ```

2. **Separate request and response schemas**:
   ```python
   # Request schemas
   UserCreate   # For POST /users
   UserUpdate   # For PATCH /users/{id}
   
   # Response schemas
   UserResponse      # Single user
   UserListResponse  # Paginated list
   ```

### Status Codes

Use appropriate HTTP status codes:
```python
# Success
200 OK              # GET, PATCH
201 Created         # POST
204 No Content      # DELETE

# Client Errors
400 Bad Request     # Invalid input
401 Unauthorized    # Authentication required
403 Forbidden       # Insufficient permissions
404 Not Found       # Resource not found
409 Conflict        # Duplicate resource

# Server Errors
500 Internal Server Error
503 Service Unavailable
```

### Pagination

Always paginate list endpoints:
```python
@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    pagination = PaginationParams(page=page, per_page=per_page)
    result = await user_crud.get_paginated(db, pagination)
    return response_handler.success(data=result)
```

## Database Standards

### SQLAlchemy Models

1. **Model structure**:
   ```python
   from sqlalchemy import String, Boolean, DateTime
   from sqlalchemy.orm import Mapped, mapped_column
   from app.core.database import Base
   
   class User(Base):
       __tablename__ = "users"
       
       # Primary key
       id: Mapped[str] = mapped_column(UUID, primary_key=True)
       
       # Required fields
       email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
       
       # Optional fields
       bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
       
       # Timestamps
       created_at: Mapped[datetime] = mapped_column(
           DateTime(timezone=True),
           default=datetime.utcnow
       )
       
       # Relationships
       posts: Mapped[List["Post"]] = relationship(
           "Post",
           back_populates="user",
           cascade="all, delete-orphan"
       )
   ```

2. **Always use UUID** for primary keys:
   ```python
   from uuid import uuid4
   
   id: Mapped[str] = mapped_column(
       UUID(as_uuid=False),
       primary_key=True,
       default=lambda: str(uuid4())
   )
   ```

3. **Index frequently queried fields**:
   ```python
   email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
   created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
   ```

### Database Operations

1. **Use dependency injection**:
   ```python
   async def get_user(
       user_id: str,
       db: AsyncSession = Depends(get_db)
   ) -> User:
       return await user_crud.get(db, user_id)
   ```

2. **Handle transactions properly**:
   ```python
   async def create_user_with_profile(
       user_data: dict,
       profile_data: dict,
       db: AsyncSession
   ):
       async with db.begin():
           user = User(**user_data)
           db.add(user)
           
           profile = Profile(**profile_data, user_id=user.id)
           db.add(profile)
           
       await db.commit()
       return user
   ```

3. **Use eager loading** to avoid N+1 queries:
   ```python
   from sqlalchemy.orm import selectinload
   
   query = select(User).options(
       selectinload(User.posts),
       selectinload(User.watchlists)
   )
   ```

### Migrations

1. **Always review auto-generated migrations**
2. **Include meaningful descriptions**:
   ```bash
   alembic revision --autogenerate -m "Add user preferences table"
   ```
3. **Test migrations** both up and down:
   ```bash
   alembic upgrade head
   alembic downgrade -1
   ```

## Service Layer Standards

### Class Design Principles

1. **Single Responsibility per Class**:
   ```python
   # Bad - Class doing too many things
   class UserService:
       def create_user(self): pass
       def authenticate_user(self): pass
       def send_email(self): pass
       def generate_report(self): pass
       def backup_data(self): pass
   
   # Good - Separate concerns into different services
   class UserService:
       """Handles user CRUD operations"""
       def create_user(self): pass
       def update_user(self): pass
       def delete_user(self): pass
   
   class AuthService:
       """Handles authentication logic"""
       def authenticate_user(self): pass
       def refresh_token(self): pass
   
   class EmailService:
       """Handles email operations"""
       def send_welcome_email(self): pass
       def send_password_reset(self): pass
   ```

2. **Keep classes focused and small**:
   - Each class should have one reason to change
   - If a class grows beyond 200-300 lines, consider splitting it
   - Use composition over inheritance

### Business Logic Separation

1. **Keep endpoints thin**:
   ```python
   # Good - Endpoint delegates to service
   @router.post("/trades")
   async def create_trade(
       trade: TradeCreate,
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_user)
   ):
       result = await trading_service.execute_trade(
           db, trade, current_user
       )
       return response_handler.success(data=result)
   ```

2. **Services handle business logic**:
   ```python
   # services/trading.py
   class TradingService:
       async def execute_trade(
           self,
           db: AsyncSession,
           trade: TradeCreate,
           user: User
       ) -> Trade:
           # Validate trade
           await self._validate_trade(trade, user)
           
           # Check balance
           if not await self._check_balance(db, user, trade):
               raise InsufficientFundsError()
           
           # Execute trade
           return await self._create_trade(db, trade, user)
   ```

### Dependency Injection

1. **Use FastAPI's dependency system**:
   ```python
   # dependencies.py
   async def get_trading_service(
       cache: CacheManager = Depends(get_cache),
       logger: AppLogger = Depends(get_logger)
   ) -> TradingService:
       return TradingService(cache=cache, logger=logger)
   ```

2. **Inject services into endpoints**:
   ```python
   @router.post("/trades")
   async def create_trade(
       trade: TradeCreate,
       service: TradingService = Depends(get_trading_service)
   ):
       return await service.execute_trade(trade)
   ```

## Error Handling

### Custom Exceptions

1. **Create domain-specific exceptions**:
   ```python
   # exceptions.py
   class TradingException(Exception):
       """Base exception for trading errors"""
       pass
   
   class InsufficientFundsError(TradingException):
       """Raised when user has insufficient funds"""
       def __init__(self, required: float, available: float):
           self.required = required
           self.available = available
           super().__init__(
               f"Insufficient funds: required {required}, "
               f"available {available}"
           )
   ```

2. **Handle exceptions consistently**:
   ```python
   @app.exception_handler(TradingException)
   async def trading_exception_handler(
       request: Request,
       exc: TradingException
   ):
       return response_handler.error(
           error_code="TRADING_ERROR",
           message=str(exc),
           status_code=400
       )
   ```

### Logging Errors

Always log errors with context:
```python
try:
    result = await external_api.fetch_data()
except Exception as e:
    logger.log_error(
        e,
        context={
            "user_id": user.id,
            "endpoint": "external_api.fetch_data",
            "request_id": request.state.request_id
        }
    )
    raise
```

### Sentry Error Monitoring

1. **Capture exceptions with context**:
   ```python
   from app.core.monitoring import ErrorMonitoring
   
   try:
       result = await process_payment(payment_data)
   except PaymentError as e:
       ErrorMonitoring.capture_exception(
           e,
           context={
               "payment_id": payment_data.id,
               "amount": payment_data.amount,
               "user_id": user.id
           },
           level="error",
           user_id=str(user.id)
       )
       raise
   ```

2. **Add breadcrumbs for complex operations**:
   ```python
   ErrorMonitoring.add_breadcrumb(
       message="Starting order processing",
       category="order",
       level="info",
       data={
           "order_id": order.id,
           "items_count": len(order.items),
           "total_amount": order.total
       }
   )
   ```

3. **Send alerts for critical issues**:
   ```python
   from app.core.monitoring import AlertManager
   
   if payment_gateway_down:
       await AlertManager.send_alert(
           title="Payment Gateway Unavailable",
           message="Primary payment processor is not responding",
           severity="critical",
           context={
               "gateway": "stripe",
               "last_success": last_successful_request
           }
       )
   ```

4. **Never send sensitive data to Sentry**:
   ```python
   # BAD - Exposes sensitive information
   ErrorMonitoring.capture_exception(e, context={
       "credit_card": card_number,  # NEVER
       "password": user_password,   # NEVER
       "ssn": social_security      # NEVER
   })
   
   # GOOD - Safe context
   ErrorMonitoring.capture_exception(e, context={
       "user_id": user.id,
       "card_last_four": card_number[-4:],
       "transaction_type": "purchase"
   })
   ```

## Testing Standards

### Test Organization

```
tests/
├── conftest.py          # Shared fixtures
├── unit/               # Unit tests
│   ├── test_models.py
│   └── test_services.py
├── integration/        # Integration tests
│   ├── test_api.py
│   └── test_database.py
└── fixtures/           # Test data
    └── users.json
```

### Test Naming

```python
# Test file naming
test_user_service.py

# Test function naming
def test_create_user_success():
    pass

def test_create_user_duplicate_email():
    pass

def test_create_user_invalid_password():
    pass
```

### Fixture Usage

```python
# conftest.py
@pytest.fixture
async def db_session():
    """Create a test database session"""
    async with async_session_maker() as session:
        yield session
        await session.rollback()

@pytest.fixture
def test_user():
    """Create a test user"""
    return User(
        id=str(uuid4()),
        email="test@example.com",
        username="testuser"
    )
```

### Test Coverage

- Minimum coverage: 80%
- Critical paths: 100%
- Focus on business logic, not boilerplate

## Documentation Standards

### Docstrings

Use Google-style docstrings:
```python
async def calculate_portfolio_value(
    user_id: str,
    date: Optional[datetime] = None
) -> Decimal:
    """Calculate the total value of a user's portfolio.
    
    Args:
        user_id: The ID of the user
        date: The date for valuation (defaults to current date)
        
    Returns:
        The total portfolio value in USD
        
    Raises:
        UserNotFoundError: If the user doesn't exist
        NoPortfolioError: If the user has no portfolio
    """
```

### API Documentation

1. **Use descriptive operation IDs**:
   ```python
   @router.get(
       "/users/{user_id}",
       response_model=UserResponse,
       summary="Get user details",
       description="Retrieve detailed information about a specific user",
       operation_id="get_user_by_id"
   )
   ```

2. **Document request/response examples**:
   ```python
   class UserResponse(BaseModel):
       """User response model"""
       id: str = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
       email: str = Field(..., example="user@example.com")
       username: str = Field(..., example="johndoe")
   ```

## Security Standards

### Authentication & Authorization

1. **Always validate permissions**:
   ```python
   async def get_portfolio(
       portfolio_id: str,
       current_user: User = Depends(get_current_user),
       db: AsyncSession = Depends(get_db)
   ):
       portfolio = await portfolio_crud.get(db, portfolio_id)
       
       if portfolio.user_id != current_user.id:
           raise HTTPException(403, "Access denied")
           
       return portfolio
   ```

2. **Sanitize inputs**:
   ```python
   # Use Pydantic validators
   class UserCreate(BaseModel):
       username: str = Field(..., regex="^[a-zA-Z0-9_-]+$")
       
       @validator("username")
       def validate_username(cls, v):
           if len(v) < 3:
               raise ValueError("Username too short")
           return v.lower()
   ```

### Sensitive Data

1. **Never log sensitive data**:
   ```python
   # Bad
   logger.info(f"User login: {username}, password: {password}")
   
   # Good
   logger.info(f"User login attempt: {username}")
   ```

2. **Hash passwords properly**:
   ```python
   from passlib.context import CryptContext
   
   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
   
   hashed_password = pwd_context.hash(password)
   is_valid = pwd_context.verify(plain_password, hashed_password)
   ```

## Performance Guidelines

### Query Optimization

1. **Use select specific columns**:
   ```python
   # Good
   query = select(User.id, User.email).where(User.is_active == True)
   
   # Bad
   query = select(User).where(User.is_active == True)
   ```

2. **Implement caching strategically**:
   ```python
   @cache(ttl=300, namespace="users")
   async def get_user_stats(user_id: str) -> dict:
       # Expensive calculation
       return stats
   ```

3. **Use bulk operations**:
   ```python
   # Good
   await db.execute(
       insert(User),
       [{"email": email, "username": username} for email, username in users]
   )
   
   # Bad
   for email, username in users:
       user = User(email=email, username=username)
       db.add(user)
       await db.commit()
   ```

### Background Tasks

Use FastAPI background tasks for non-critical operations:
```python
from fastapi import BackgroundTasks

@router.post("/users")
async def create_user(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    new_user = await user_service.create_user(db, user)
    
    # Send welcome email in background
    background_tasks.add_task(
        email_service.send_welcome_email,
        new_user.email
    )
    
    return new_user
```

### Performance Monitoring with Sentry

1. **Monitor slow operations**:
   ```python
   from app.core.monitoring import monitor_performance
   
   @monitor_performance("external_api")
   async def fetch_market_data(symbol: str):
       """Fetch real-time market data - monitored for performance"""
       return await polygon_service.get_quote(symbol)
   ```

2. **Manual transaction monitoring**:
   ```python
   import sentry_sdk
   
   async def process_bulk_orders(orders: List[Order]):
       with sentry_sdk.start_transaction(op="task", name="bulk_order_processing") as transaction:
           transaction.set_tag("order_count", len(orders))
           
           for order in orders:
               with sentry_sdk.start_span(op="process_order") as span:
                   span.set_data("order_id", order.id)
                   await process_single_order(order)
   ```

3. **Set up performance thresholds**:
   ```python
   # In app/core/config.py
   sentry_traces_sample_rate: float = 0.1  # Sample 10% of transactions in production
   
   # For specific operations, you can override:
   @monitor_performance("critical_operation", sample_rate=1.0)  # Always monitor
   async def critical_payment_processing():
       pass
   ```

## Code Review Checklist

Before submitting code for review, ensure:

- [ ] Code follows PEP 8 and passes Black/Ruff
- [ ] All functions have type hints
- [ ] Functions follow Single Responsibility Principle
- [ ] No function exceeds 30 lines
- [ ] No file exceeds 500 lines
- [ ] Classes have a single, clear purpose
- [ ] Complex functions have docstrings
- [ ] New endpoints have OpenAPI documentation
- [ ] Database queries are optimized
- [ ] Errors are handled appropriately
- [ ] Sensitive data is not logged
- [ ] Critical errors are captured with Sentry
- [ ] Performance monitoring added for slow operations
- [ ] User context set for Sentry where appropriate
- [ ] Tests are written and passing
- [ ] No commented-out code
- [ ] No print statements (use logger)
- [ ] Dependencies are injected properly
- [ ] Business logic is in services, not endpoints