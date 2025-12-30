import discord
from discord.ext import commands
import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger('BankerBot.UnbelievaBoat')

class UnbelievaBoat(commands.Cog):
    """Handles all interactions with the UnbelievaBoat API."""
    
    BASE_URL = "https://unbelievaboat.com/api"
    
    def __init__(self, bot):
        self.bot = bot
        self.api_key = bot.config['unb_api_key']
        self.api_delay = bot.config['api_delay']
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def cog_load(self):
        """Called when the cog is loaded."""
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': self.api_key,
                'Accept': 'application/json'
            }
        )
        logger.info('UnbelievaBoat API session initialized')
    
    async def cog_unload(self):
        """Called when the cog is unloaded."""
        if self.session:
            await self.session.close()
            logger.info('UnbelievaBoat API session closed')
    
    async def _make_request(self, method: str, endpoint: str, 
                           json_data: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make a request to the UnbelievaBoat API with rate limiting."""
        if not self.session:
            logger.error('API session not initialized')
            return None
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            # Rate limiting
            await asyncio.sleep(self.api_delay)
            
            async with self.session.request(method, url, json=json_data) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f'API request successful: {method} {endpoint}')
                    return data
                elif response.status == 429:
                    # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f'Rate limited, retrying after {retry_after}s')
                    await asyncio.sleep(retry_after)
                    return await self._make_request(method, endpoint, json_data)
                elif response.status == 404:
                    logger.error(f'Resource not found: {endpoint}')
                    return None
                elif response.status == 403:
                    logger.error(f'Forbidden: Check API permissions for {endpoint}')
                    return None
                else:
                    error_text = await response.text()
                    logger.error(f'API error {response.status}: {error_text}')
                    return None
        except aiohttp.ClientError as e:
            logger.error(f'Network error during API request: {e}')
            return None
        except Exception as e:
            logger.error(f'Unexpected error during API request: {e}')
            return None
    
    # ========================================================================
    # USER BALANCE OPERATIONS
    # ========================================================================
    
    async def get_user_balance(self, guild_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a user's balance in a specific guild.
        
        Returns:
            Dict with 'cash', 'bank', and 'total' keys, or None if error
        """
        endpoint = f"/guilds/{guild_id}/users/{user_id}"
        data = await self._make_request('GET', endpoint)
        
        if data:
            return {
                'cash': float(data.get('cash', 0)),
                'bank': float(data.get('bank', 0)),
                'total': float(data.get('total', 0)),
                'rank': data.get('rank')
            }
        return None
    
    async def set_user_balance(self, guild_id: int, user_id: int, 
                              cash: Optional[float] = None, 
                              bank: Optional[float] = None,
                              reason: str = "BankerBot transfer") -> Optional[Dict[str, Any]]:
        """
        Set a user's balance in a specific guild.
        
        Args:
            guild_id: The Discord guild ID
            user_id: The Discord user ID
            cash: New cash balance (if provided)
            bank: New bank balance (if provided)
            reason: Reason for the change (for audit purposes)
        
        Returns:
            Updated balance data or None if error
        """
        endpoint = f"/guilds/{guild_id}/users/{user_id}"
        
        json_data = {'reason': reason}
        if cash is not None:
            json_data['cash'] = str(cash)  # UNB API expects strings for numbers
        if bank is not None:
            json_data['bank'] = str(bank)
        
        data = await self._make_request('PATCH', endpoint, json_data)
        
        if data:
            return {
                'cash': float(data.get('cash', 0)),
                'bank': float(data.get('bank', 0)),
                'total': float(data.get('total', 0))
            }
        return None
    
    async def modify_user_balance(self, guild_id: int, user_id: int,
                                 cash_change: Optional[float] = None,
                                 bank_change: Optional[float] = None,
                                 reason: str = "BankerBot transfer") -> Optional[Dict[str, Any]]:
        """
        Modify a user's balance by adding or subtracting amounts.
        
        Args:
            guild_id: The Discord guild ID
            user_id: The Discord user ID
            cash_change: Amount to add/subtract from cash (positive or negative)
            bank_change: Amount to add/subtract from bank (positive or negative)
            reason: Reason for the change
        
        Returns:
            Updated balance data or None if error
        """
        # First, get current balance
        current = await self.get_user_balance(guild_id, user_id)
        if not current:
            logger.error(f'Could not get current balance for user {user_id} in guild {guild_id}')
            return None
        
        # Calculate new balances
        new_cash = current['cash']
        new_bank = current['bank']
        
        if cash_change is not None:
            new_cash += cash_change
        if bank_change is not None:
            new_bank += bank_change
        
        # Ensure balances don't go negative
        if new_cash < 0 or new_bank < 0:
            logger.error(f'Balance modification would result in negative balance')
            return None
        
        # Set new balances
        return await self.set_user_balance(guild_id, user_id, new_cash, new_bank, reason)
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    async def validate_guild_access(self, guild_id: int) -> bool:
        """
        Validate that the bot has API access to a guild.
        
        Returns:
            True if access is valid, False otherwise
        """
        endpoint = f"/guilds/{guild_id}"
        data = await self._make_request('GET', endpoint)
        return data is not None
    
    async def user_has_sufficient_balance(self, guild_id: int, user_id: int,
                                         amount: float, wallet_type: str) -> bool:
        """
        Check if a user has sufficient balance for a transfer.
        
        Args:
            guild_id: The Discord guild ID
            user_id: The Discord user ID
            amount: Amount needed
            wallet_type: 'cash' or 'bank'
        
        Returns:
            True if user has sufficient balance, False otherwise
        """
        balance = await self.get_user_balance(guild_id, user_id)
        if not balance:
            return False
        
        if wallet_type.lower() == 'cash':
            return balance['cash'] >= amount
        elif wallet_type.lower() == 'bank':
            return balance['bank'] >= amount
        return False

async def setup(bot):
    await bot.add_cog(UnbelievaBoat(bot))
