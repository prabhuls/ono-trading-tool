#!/usr/bin/env python3
"""
Test Railway Database Connection
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

# Show environment status
print("=" * 60)
print("Environment Configuration:")
print("=" * 60)
db_url = os.getenv("DATABASE_URL")
if db_url:
    # Hide password in display
    import re
    safe_url = re.sub(r':([^:@]+)@', ':****@', db_url)
    print(f"DATABASE_URL: {safe_url}")
else:
    print("DATABASE_URL: NOT SET")

print(f"ENABLE_DATABASE: {os.getenv('ENABLE_DATABASE', 'true')}")
print(f"ENVIRONMENT: {os.getenv('ENVIRONMENT', 'development')}")
print("=" * 60)

async def test_basic_connection():
    """Test basic database connection"""
    print("\n1. Testing basic connection with asyncpg...")
    try:
        import asyncpg
        
        # Get connection URL and convert to asyncpg format
        db_url = os.getenv("DATABASE_URL")
        if db_url and db_url.startswith("postgresql://"):
            # asyncpg uses postgresql:// format directly
            conn = await asyncpg.connect(db_url, timeout=10)
            
            # Test query
            result = await conn.fetchval("SELECT version()")
            print(f"✓ Connected to PostgreSQL!")
            print(f"  Version: {result}")
            
            # Check current database
            db_name = await conn.fetchval("SELECT current_database()")
            print(f"  Database: {db_name}")
            
            await conn.close()
            return True
            
    except ImportError:
        print("✗ asyncpg not installed. Install with: pip install asyncpg")
        return False
    except asyncio.TimeoutError:
        print("✗ Connection timeout after 10 seconds")
        return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

async def test_sqlalchemy_connection():
    """Test SQLAlchemy connection"""
    print("\n2. Testing SQLAlchemy connection...")
    try:
        from app.core.database import get_async_session
        from sqlalchemy import text
        
        async for session in get_async_session():
            result = await session.execute(text("SELECT 1"))
            print("✓ SQLAlchemy connection successful!")
            
            # Check tables
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = result.fetchall()
            
            print(f"  Found {len(tables)} tables:")
            for table in tables:
                print(f"    - {table[0]}")
            
            # Check specific cleanup tables
            cleanup_tables = ['todays_movers', 'main_lists', 'last_7_days_movers', 'transfer_status']
            for table_name in cleanup_tables:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                print(f"  {table_name}: {count} records")
            
            await session.close()
            return True
            
    except Exception as e:
        print(f"✗ SQLAlchemy connection failed: {type(e).__name__}: {e}")
        return False

async def test_cleanup_tables():
    """Check if cleanup tables exist and have data"""
    print("\n3. Checking cleanup-specific tables...")
    try:
        from app.core.database import get_async_session
        from sqlalchemy import text
        
        async for session in get_async_session():
            # Check if transfer was already done today
            result = await session.execute(text("""
                SELECT transfer_date, daily_transfer_completed, transferred_at
                FROM transfer_status
                ORDER BY transfer_date DESC
                LIMIT 5
            """))
            transfers = result.fetchall()
            
            if transfers:
                print("  Recent transfers:")
                for transfer in transfers:
                    print(f"    - {transfer[0]}: {'✓ Completed' if transfer[1] else '✗ Failed'} at {transfer[2]}")
            else:
                print("  No transfer history found")
            
            await session.close()
            return True
            
    except Exception as e:
        print(f"✗ Error checking tables: {e}")
        return False

async def main():
    """Run all tests"""
    print("\nStarting Railway Database Connection Tests...")
    print("=" * 60)
    
    # Test connections
    basic_ok = await test_basic_connection()
    
    if basic_ok:
        sqlalchemy_ok = await test_sqlalchemy_connection()
        
        if sqlalchemy_ok:
            await test_cleanup_tables()
            print("\n" + "=" * 60)
            print("✓ All tests passed! Database is ready.")
            print("You can now run: python run_commands/run_daily_cleanup.py")
        else:
            print("\n" + "=" * 60)
            print("✗ SQLAlchemy connection failed.")
            print("Check if all tables are created: alembic upgrade head")
    else:
        print("\n" + "=" * 60)
        print("✗ Basic connection failed. Check your DATABASE_URL.")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())