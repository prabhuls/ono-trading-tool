# Database Setup Guide

This guide covers PostgreSQL database setup for the Trading Tools platform using SQLAlchemy ORM with Alembic for migrations.

## Table of Contents
- [Quick Start](#quick-start)
- [Local Development Setup](#local-development-setup)
- [Railway PostgreSQL Setup](#railway-postgresql-setup)
- [SQLAlchemy Models](#sqlalchemy-models)
- [Alembic Migrations](#alembic-migrations)
- [Database Operations](#database-operations)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Quick Start

The boilerplate uses PostgreSQL with SQLAlchemy ORM for all database operations:

1. **Start PostgreSQL locally**:
   ```bash
   docker-compose up -d postgres
   ```

2. **Run migrations**:
   ```bash
   cd server
   alembic upgrade head
   ```

3. **Your database is ready!** The initial migration creates:
   - Users table (authentication)
   - API Keys table (encrypted external API storage)
   - Watchlists table (example domain model)

## Local Development Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.9+
- PostgreSQL client tools (optional but helpful)

### 1. Start PostgreSQL with Docker

```bash
# From project root
docker-compose up -d postgres

# Verify it's running
docker-compose ps
docker-compose logs postgres
```

This starts PostgreSQL with:
- Host: `localhost`
- Port: `5432`
- Database: `trading_tools`
- Username: `postgres`
- Password: `password`

### 2. Configure Environment

Update your `.env` file:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_tools
```

For async SQLAlchemy, the URL is automatically converted to:
```
postgresql+asyncpg://postgres:password@localhost:5432/trading_tools
```

### 3. Initialize Database

```bash
cd server
source venv/bin/activate

# Create all tables (without migrations)
python -c "from app.core.database import DatabaseManager; import asyncio; asyncio.run(DatabaseManager.create_all())"

# Or use Alembic migrations (recommended)
alembic upgrade head
```

## Railway PostgreSQL Setup

### 1. Add PostgreSQL to Railway

In your Railway project:
1. Click "New" → "Database" → "Add PostgreSQL"
2. PostgreSQL will be provisioned automatically
3. Note the connection string in the Variables tab

### 2. Configure Backend Service

In your backend service environment variables:
```env
# Railway provides this automatically
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

### 3. Run Migrations on Deploy

Add to your `Dockerfile`:
```dockerfile
# Run migrations before starting the app
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Or create a release phase in `railway.json`:
```json
{
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "releaseCommand": "alembic upgrade head"
  }
}
```

## SQLAlchemy Models

### Model Structure

Models are defined in `app/models/` using SQLAlchemy 2.0 style:

```python
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(UUID, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

### Creating New Models

1. Create a new file in `app/models/`:
```python
# app/models/portfolio.py
from sqlalchemy import String, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id: Mapped[str] = mapped_column(UUID, primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    total_value: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="portfolios")
```

2. Import in `app/models/__init__.py`:
```python
from app.models.portfolio import Portfolio
```

3. Create migration:
```bash
alembic revision --autogenerate -m "Add portfolio model"
alembic upgrade head
```

## Alembic Migrations

### Configuration

Alembic is configured in `alembic.ini` and `alembic/env.py`.

### Common Commands

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# Show current revision
alembic current

# Generate SQL without applying
alembic upgrade head --sql
```

### Manual Migration Example

```bash
# Create empty migration
alembic revision -m "Add custom index"
```

Edit the generated file:
```python
def upgrade():
    op.create_index('idx_users_email_lower', 'users', 
                    [sa.text('lower(email)')], unique=True)

def downgrade():
    op.drop_index('idx_users_email_lower', 'users')
```

## Database Operations

### Using DatabaseCRUD

The boilerplate includes a generic CRUD class in `app/utils/database.py`:

```python
from app.utils.database import DatabaseCRUD
from app.models.user import User

# Create CRUD instance
user_crud = DatabaseCRUD[User](User)

# In your endpoint
async def get_users(db: AsyncSession = Depends(get_db)):
    users = await user_crud.get_multi(db, limit=10)
    return users
```

### Direct Queries

For complex queries, use SQLAlchemy directly:

```python
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

async def get_user_with_watchlists(user_id: str, db: AsyncSession):
    query = (
        select(User)
        .options(selectinload(User.watchlists))
        .where(User.id == user_id)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()
```

### Transactions

Use the `@transactional` decorator for multi-step operations:

```python
from app.core.database import transactional

@transactional
async def create_user_with_portfolio(db: AsyncSession, user_data, portfolio_data):
    user = User(**user_data)
    db.add(user)
    
    portfolio = Portfolio(**portfolio_data, user=user)
    db.add(portfolio)
    
    return user
```

### Pagination

Use the pagination utilities:

```python
from app.utils.database import PaginationParams, PaginatedResponse

async def list_users(
    page: int = 1,
    per_page: int = 50,
    db: AsyncSession = Depends(get_db)
):
    pagination = PaginationParams(page=page, per_page=per_page)
    result = await user_crud.get_paginated(db, pagination)
    return result
```

## Best Practices

### 1. Model Design

- Use UUID primary keys for better distribution
- Add indexes for frequently queried fields
- Use appropriate field lengths and constraints
- Enable cascade deletes where appropriate

### 2. Async Best Practices

```python
# Good - Single query
users = await db.execute(select(User).where(User.is_active == True))

# Bad - N+1 queries
for user in users:
    watchlists = await db.execute(select(Watchlist).where(Watchlist.user_id == user.id))

# Good - Eager loading
users = await db.execute(
    select(User)
    .options(selectinload(User.watchlists))
    .where(User.is_active == True)
)
```

### 3. Migration Best Practices

- Always review auto-generated migrations
- Test migrations on a copy of production data
- Include both `upgrade()` and `downgrade()` functions
- Use descriptive migration messages
- Never edit applied migrations

### 4. Connection Management

The boilerplate handles connections automatically, but remember:
- Use dependency injection for database sessions
- Sessions are automatically committed on success
- Sessions are automatically rolled back on error
- Always use async operations

### 5. Query Optimization

```python
# Use select specific columns
query = select(User.id, User.email).where(User.is_active == True)

# Use joins efficiently
query = (
    select(User, func.count(Watchlist.id))
    .join(Watchlist, User.id == Watchlist.user_id, isouter=True)
    .group_by(User.id)
)

# Use bulk operations
await user_crud.bulk_create(db, User, user_list)
```

## Environment Variables

### Development
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_tools
```

### Production (Railway)
```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

### Testing
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_tools_test
```

## Common Patterns

### Soft Deletes

Add to your models:
```python
class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

### Audit Trails

```python
class AuditMixin:
    created_by: Mapped[str | None] = mapped_column(UUID, ForeignKey("users.id"))
    updated_by: Mapped[str | None] = mapped_column(UUID, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## Troubleshooting

### Connection Issues

```bash
# Test connection
psql postgresql://postgres:password@localhost:5432/trading_tools

# Check Docker logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Migration Issues

```bash
# Check current revision
alembic current

# Show migration SQL without applying
alembic upgrade head --sql

# Force revision state (use carefully!)
alembic stamp head
```

### Performance Issues

1. Check slow queries:
```sql
SELECT query, calls, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

2. Add indexes:
```python
# In your model
__table_args__ = (
    Index('idx_user_email_lower', func.lower(email), unique=True),
    Index('idx_created_at', created_at.desc()),
)
```

3. Use query analysis:
```python
# Log SQL statements
engine = create_async_engine(url, echo=True)
```

## Resources

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [FastAPI with SQLAlchemy](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [Async SQLAlchemy Guide](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
