"""
Daily Cleanup Worker
Transfers Today's Movers → Main Lists → 7-Day Archive
Cleans up records older than 7 days from archive
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, List
from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movers import TodaysMover, MainList
from app.models.archive import Last7DaysMovers, TransferStatus
from app.core.database import get_async_session

logger = logging.getLogger(__name__)


class DailyCleanupWorker:
    """Handles daily transfer and cleanup operations"""
    
    def __init__(self):
        self.transferred_count = 0
        self.archived_count = 0
        self.cleaned_count = 0
        self.updated_archive_count = 0
        self.start_time = None
    
    async def check_transfer_status(self, session: AsyncSession, transfer_date: date) -> bool:
        """Check if transfer was already completed today"""
        result = await session.execute(
            select(TransferStatus)
            .where(TransferStatus.transfer_date == transfer_date)
        )
        status = result.scalar_one_or_none()
        return status.daily_transfer_completed if status else False
    
    async def get_todays_movers(self, session: AsyncSession) -> List[TodaysMover]:
        """Get all records from Today's Movers"""
        result = await session.execute(
            select(TodaysMover)
            .order_by(TodaysMover.symbol)
        )
        return result.scalars().all()
    
    async def get_main_lists(self, session: AsyncSession) -> List[MainList]:
        """Get all records from Main Lists"""
        result = await session.execute(
            select(MainList)
            .where(MainList.is_active == True)
            .order_by(MainList.symbol)
        )
        return result.scalars().all()
    
    async def archive_main_list_record(self, session: AsyncSession, record: MainList) -> bool:
        """Archive or update a Main List record in 7-day archive"""
        try:
            # Check if symbol already exists in archive
            result = await session.execute(
                select(Last7DaysMovers)
                .where(Last7DaysMovers.symbol == record.symbol)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing record with new timestamp
                existing.last_seen_at = datetime.utcnow()
                existing.mover_type = record.list_type
                existing.current_price = record.last_price
                existing.special_character = record.special_character
                existing.has_weeklies = record.has_weeklies if hasattr(record, 'has_weeklies') else False
                existing.passed_variability_check = record.passed_variability_check
                self.updated_archive_count += 1
                logger.debug(f"Updated archive record for {record.symbol}")
            else:
                # Insert new archive record
                new_archive = Last7DaysMovers(
                    symbol=record.symbol,
                    last_seen_at=datetime.utcnow(),
                    mover_type=record.list_type,
                    current_price=record.last_price,
                    special_character=record.special_character,
                    has_weeklies=record.has_weeklies if hasattr(record, 'has_weeklies') else False,
                    passed_variability_check=record.passed_variability_check
                )
                session.add(new_archive)
                self.archived_count += 1
                logger.debug(f"Archived new record for {record.symbol}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error archiving record for {record.symbol}: {e}")
            return False
    
    async def transfer_mover_to_main_list(self, session: AsyncSession, mover: TodaysMover) -> bool:
        """Transfer a Today's Mover to Main List"""
        try:
            # Create new Main List record from Today's Mover
            new_main = MainList(
                symbol=mover.symbol,
                name=mover.name,
                list_type=mover.mover_type,  # uptrend or downtrend
                last_price=mover.current_price,
                passed_variability_check=mover.passed_variability_check,
                special_character=mover.special_character,
                added_date=date.today(),
                last_updated=datetime.utcnow(),
                is_active=True
            )
            session.add(new_main)
            self.transferred_count += 1
            logger.debug(f"Transferred {mover.symbol} to Main List")
            return True
            
        except Exception as e:
            logger.error(f"Error transferring {mover.symbol}: {e}")
            return False
    
    async def clean_expired_archives(self, session: AsyncSession) -> int:
        """Remove archive records older than 7 days"""
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        # Get count before deletion for logging
        result = await session.execute(
            select(Last7DaysMovers)
            .where(Last7DaysMovers.last_seen_at < seven_days_ago)
        )
        expired_records = result.scalars().all()
        expired_count = len(expired_records)
        
        if expired_count > 0:
            # Log which symbols are being removed
            expired_symbols = [r.symbol for r in expired_records]
            logger.info(f"Removing {expired_count} expired records: {', '.join(expired_symbols[:10])}")
            if expired_count > 10:
                logger.info(f"... and {expired_count - 10} more")
            
            # Delete expired records
            await session.execute(
                delete(Last7DaysMovers)
                .where(Last7DaysMovers.last_seen_at < seven_days_ago)
            )
            self.cleaned_count = expired_count
        
        return expired_count
    
    async def record_transfer_status(
        self, 
        session: AsyncSession, 
        transfer_date: date,
        success: bool = True
    ) -> None:
        """Record the transfer status"""
        try:
            # Check if status record exists
            result = await session.execute(
                select(TransferStatus)
                .where(TransferStatus.transfer_date == transfer_date)
            )
            status = result.scalar_one_or_none()
            
            if status:
                # Update existing record
                status.daily_transfer_completed = success
                status.transferred_at = datetime.utcnow()
                status.records_transferred = self.transferred_count
                status.records_archived = self.archived_count + self.updated_archive_count
                status.records_cleaned = self.cleaned_count
            else:
                # Create new record
                new_status = TransferStatus(
                    transfer_date=transfer_date,
                    daily_transfer_completed=success,
                    transferred_at=datetime.utcnow(),
                    records_transferred=self.transferred_count,
                    records_archived=self.archived_count + self.updated_archive_count,
                    records_cleaned=self.cleaned_count
                )
                session.add(new_status)
            
            await session.commit()
            logger.info(f"Transfer status recorded for {transfer_date}")
            
        except Exception as e:
            logger.error(f"Error recording transfer status: {e}")
    
    async def run(self) -> Dict:
        """Execute the daily cleanup process"""
        self.start_time = datetime.utcnow()
        logger.info("=" * 60)
        logger.info("Starting Daily Cleanup Worker")
        logger.info("=" * 60)
        
        transfer_date = date.today()
        
        async for session in get_async_session():
            try:
                # Check if transfer was already completed today
                if await self.check_transfer_status(session, transfer_date):
                    logger.warning(f"Transfer already completed for {transfer_date}")
                    return {
                        'success': False,
                        'message': f'Transfer already completed for {transfer_date}',
                        'execution_time': 0
                    }
                
                # Step 1: Get all current data
                logger.info("Step 1: Fetching current data...")
                todays_movers = await self.get_todays_movers(session)
                main_lists = await self.get_main_lists(session)
                
                logger.info(f"Found {len(todays_movers)} Today's Movers")
                logger.info(f"Found {len(main_lists)} Main List records")
                
                # Step 2: Archive current Main Lists to 7-day archive
                logger.info("Step 2: Archiving Main Lists to 7-day archive...")
                for record in main_lists:
                    await self.archive_main_list_record(session, record)
                
                logger.info(f"Archived {self.archived_count} new records")
                logger.info(f"Updated {self.updated_archive_count} existing records")
                
                # Step 3: Clear Main Lists table
                logger.info("Step 3: Clearing Main Lists table...")
                await session.execute(delete(MainList))
                logger.info(f"Cleared {len(main_lists)} records from Main Lists")
                
                # Step 4: Transfer Today's Movers to Main Lists
                logger.info("Step 4: Transferring Today's Movers to Main Lists...")
                for mover in todays_movers:
                    await self.transfer_mover_to_main_list(session, mover)
                
                logger.info(f"Transferred {self.transferred_count} records to Main Lists")
                
                # Step 5: Clear Today's Movers table
                logger.info("Step 5: Clearing Today's Movers table...")
                await session.execute(delete(TodaysMover))
                logger.info(f"Cleared {len(todays_movers)} records from Today's Movers")
                
                # Step 6: Clean up expired archive records (> 7 days old)
                logger.info("Step 6: Cleaning expired archive records...")
                await self.clean_expired_archives(session)
                logger.info(f"Removed {self.cleaned_count} expired records from archive")
                
                # Step 7: Record transfer status
                logger.info("Step 7: Recording transfer status...")
                await self.record_transfer_status(session, transfer_date, success=True)
                
                # Commit all changes
                await session.commit()
                
                execution_time = (datetime.utcnow() - self.start_time).total_seconds()
                
                logger.info("=" * 60)
                logger.info("Daily Cleanup Completed Successfully")
                logger.info(f"Transferred: {self.transferred_count} records")
                logger.info(f"Archived (new): {self.archived_count} records")
                logger.info(f"Archived (updated): {self.updated_archive_count} records")
                logger.info(f"Cleaned: {self.cleaned_count} expired records")
                logger.info(f"Execution time: {execution_time:.2f} seconds")
                logger.info("=" * 60)
                
                return {
                    'success': True,
                    'transferred': self.transferred_count,
                    'archived_new': self.archived_count,
                    'archived_updated': self.updated_archive_count,
                    'cleaned': self.cleaned_count,
                    'execution_time': execution_time
                }
                
            except Exception as e:
                logger.error(f"Error in daily cleanup: {e}")
                await session.rollback()
                
                # Record failure status
                await self.record_transfer_status(session, transfer_date, success=False)
                
                return {
                    'success': False,
                    'error': str(e),
                    'execution_time': (datetime.utcnow() - self.start_time).total_seconds()
                }


async def run_daily_cleanup() -> Dict:
    """Entry point for daily cleanup worker"""
    worker = DailyCleanupWorker()
    return await worker.run()