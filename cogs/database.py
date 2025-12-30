import discord
from discord.ext import commands
import aiosqlite
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger('BankerBot.Database')

class Database(commands.Cog):
    """Handles all database operations for BankerBot."""
    
    def __init__(self, bot):
        self.bot = bot
        self.db_path = 'bankerbot.db'
        bot.loop.create_task(self.init_database())
    
    async def init_database(self):
        """Initialize database tables."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Economies table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS economies (
                        guild_id INTEGER PRIMARY KEY,
                        guild_name TEXT NOT NULL,
                        currency_name TEXT NOT NULL,
                        currency_symbol TEXT NOT NULL,
                        rate_usd REAL NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        application_note TEXT,
                        applied_by INTEGER NOT NULL,
                        applied_at TEXT NOT NULL,
                        approved_at TEXT,
                        approved_by INTEGER
                    )
                ''')
                
                # Transfers table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS transfers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        from_guild_id INTEGER NOT NULL,
                        to_guild_id INTEGER NOT NULL,
                        amount_source REAL NOT NULL,
                        amount_target REAL NOT NULL,
                        source_currency TEXT NOT NULL,
                        target_currency TEXT NOT NULL,
                        wallet_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        exchange_rate REAL NOT NULL
                    )
                ''')
                
                # Approved officers table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS approved_officers (
                        user_id INTEGER PRIMARY KEY,
                        added_at TEXT NOT NULL,
                        added_by INTEGER NOT NULL
                    )
                ''')
                
                # Audit log table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        guild_id INTEGER,
                        details TEXT,
                        timestamp TEXT NOT NULL
                    )
                ''')
                
                await db.commit()
                logger.info('Database initialized successfully')
        except Exception as e:
            logger.error(f'Failed to initialize database: {e}')
    
    # ========================================================================
    # ECONOMY OPERATIONS
    # ========================================================================
    
    async def add_economy(self, guild_id: int, guild_name: str, currency_name: str,
                         currency_symbol: str, rate_usd: float, applied_by: int,
                         application_note: Optional[str] = None) -> bool:
        """Add a new economy application."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO economies 
                    (guild_id, guild_name, currency_name, currency_symbol, 
                     rate_usd, status, application_note, applied_by, applied_at)
                    VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)
                ''', (guild_id, guild_name, currency_name, currency_symbol, 
                      rate_usd, application_note, applied_by, datetime.utcnow().isoformat()))
                await db.commit()
                logger.info(f'Added economy application for guild {guild_id}')
                return True
        except aiosqlite.IntegrityError:
            logger.warning(f'Economy for guild {guild_id} already exists')
            return False
        except Exception as e:
            logger.error(f'Failed to add economy: {e}')
            return False
    
    async def get_economy(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get economy information for a specific guild."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    'SELECT * FROM economies WHERE guild_id = ?', (guild_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
        except Exception as e:
            logger.error(f'Failed to get economy: {e}')
            return None
    
    async def get_all_economies(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all economies, optionally filtered by status."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                if status:
                    query = 'SELECT * FROM economies WHERE status = ? ORDER BY applied_at DESC'
                    params = (status,)
                else:
                    query = 'SELECT * FROM economies ORDER BY applied_at DESC'
                    params = ()
                
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f'Failed to get economies: {e}')
            return []
    
    async def update_economy_status(self, guild_id: int, status: str, 
                                   approved_by: Optional[int] = None) -> bool:
        """Update the status of an economy (approved/rejected)."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if status == 'approved' and approved_by:
                    await db.execute('''
                        UPDATE economies 
                        SET status = ?, approved_at = ?, approved_by = ?
                        WHERE guild_id = ?
                    ''', (status, datetime.utcnow().isoformat(), approved_by, guild_id))
                else:
                    await db.execute('''
                        UPDATE economies SET status = ? WHERE guild_id = ?
                    ''', (status, guild_id))
                await db.commit()
                logger.info(f'Updated economy {guild_id} status to {status}')
                return True
        except Exception as e:
            logger.error(f'Failed to update economy status: {e}')
            return False
    
    async def remove_economy(self, guild_id: int) -> bool:
        """Remove an economy from the database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('DELETE FROM economies WHERE guild_id = ?', (guild_id,))
                await db.commit()
                logger.info(f'Removed economy {guild_id}')
                return True
        except Exception as e:
            logger.error(f'Failed to remove economy: {e}')
            return False
    
    # ========================================================================
    # TRANSFER OPERATIONS
    # ========================================================================
    
    async def log_transfer(self, user_id: int, from_guild_id: int, to_guild_id: int,
                          amount_source: float, amount_target: float,
                          source_currency: str, target_currency: str,
                          wallet_type: str, exchange_rate: float) -> bool:
        """Log a currency transfer."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO transfers 
                    (user_id, from_guild_id, to_guild_id, amount_source, 
                     amount_target, source_currency, target_currency, 
                     wallet_type, timestamp, exchange_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, from_guild_id, to_guild_id, amount_source,
                      amount_target, source_currency, target_currency,
                      wallet_type, datetime.utcnow().isoformat(), exchange_rate))
                await db.commit()
                logger.info(f'Logged transfer for user {user_id}')
                return True
        except Exception as e:
            logger.error(f'Failed to log transfer: {e}')
            return False
    
    async def get_user_transfers(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent transfers for a user."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute('''
                    SELECT * FROM transfers 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (user_id, limit)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f'Failed to get user transfers: {e}')
            return []
    
    async def cleanup_old_transfers(self, days: int = 180) -> int:
        """Delete transfers older than specified days."""
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'DELETE FROM transfers WHERE timestamp < ?', (cutoff_date,)
                )
                deleted = cursor.rowcount
                await db.commit()
                logger.info(f'Cleaned up {deleted} old transfers')
                return deleted
        except Exception as e:
            logger.error(f'Failed to cleanup transfers: {e}')
            return 0
    
    # ========================================================================
    # OFFICER OPERATIONS
    # ========================================================================
    
    async def add_officer(self, user_id: int, added_by: int) -> bool:
        """Add an approved officer."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO approved_officers (user_id, added_at, added_by)
                    VALUES (?, ?, ?)
                ''', (user_id, datetime.utcnow().isoformat(), added_by))
                await db.commit()
                logger.info(f'Added officer {user_id}')
                return True
        except aiosqlite.IntegrityError:
            logger.warning(f'Officer {user_id} already exists')
            return False
        except Exception as e:
            logger.error(f'Failed to add officer: {e}')
            return False
    
    async def remove_officer(self, user_id: int) -> bool:
        """Remove an approved officer."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('DELETE FROM approved_officers WHERE user_id = ?', (user_id,))
                await db.commit()
                logger.info(f'Removed officer {user_id}')
                return True
        except Exception as e:
            logger.error(f'Failed to remove officer: {e}')
            return False
    
    async def is_officer(self, user_id: int) -> bool:
        """Check if a user is an approved officer."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    'SELECT 1 FROM approved_officers WHERE user_id = ?', (user_id,)
                ) as cursor:
                    result = await cursor.fetchone()
                    return result is not None
        except Exception as e:
            logger.error(f'Failed to check officer status: {e}')
            return False
    
    async def get_all_officers(self) -> List[Dict[str, Any]]:
        """Get all approved officers."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute('SELECT * FROM approved_officers') as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f'Failed to get officers: {e}')
            return []
    
    # ========================================================================
    # AUDIT LOG
    # ========================================================================
    
    async def log_action(self, action: str, user_id: int, 
                        guild_id: Optional[int] = None, details: Optional[str] = None) -> bool:
        """Log an action to the audit log."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO audit_log (action, user_id, guild_id, details, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (action, user_id, guild_id, details, datetime.utcnow().isoformat()))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f'Failed to log action: {e}')
            return False

async def setup(bot):
    await bot.add_cog(Database(bot))
