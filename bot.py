import discord
from discord.ext import commands
import asyncio
import aiohttp
import logging
from typing import Optional
import sys

# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================================================
DISCORD_TOKEN = "YOUR_DISCORD_BOT_TOKEN_HERE"
UNB_API_KEY = "YOUR_UNBELIEVABOAT_API_KEY_HERE"
CENTRAL_BANK_SERVER_ID = 1234567890  # Replace with your Central Bank server ID
APPROVAL_CHANNEL_ID = 1234567890  # Replace with approval channel ID
OWNER_USER_ID = 1234567890  # Your Discord user ID for managing officers

# ============================================================================
# LOGGING SETUP
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bankerbot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('BankerBot')

# ============================================================================
# BOT SETUP
# ============================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Store configuration in bot instance for access by cogs
bot.config = {
    'unb_api_key': UNB_API_KEY,
    'central_bank_server_id': CENTRAL_BANK_SERVER_ID,
    'approval_channel_id': APPROVAL_CHANNEL_ID,
    'owner_user_id': OWNER_USER_ID,
    'api_delay': 1.0,  # Rate limit delay for API calls
    'min_exchange_rate': 0.01,
    'max_exchange_rate': 10000.0,
    'min_transfer_amount': 1.0,
    'max_transfer_amount': 1000000.0
}

# ============================================================================
# EVENT HANDLERS
# ============================================================================
@bot.event
async def on_ready():
    """Called when the bot successfully connects to Discord."""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} command(s)')
    except Exception as e:
        logger.error(f'Failed to sync commands: {e}')
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="the global economy"
        )
    )

@bot.event
async def on_guild_join(guild):
    """Called when the bot joins a new server."""
    logger.info(f'Joined new guild: {guild.name} (ID: {guild.id})')

@bot.event
async def on_guild_remove(guild):
    """Called when the bot leaves a server."""
    logger.info(f'Left guild: {guild.name} (ID: {guild.id})')

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for traditional commands."""
    if isinstance(error, commands.CommandNotFound):
        return
    logger.error(f'Command error: {error}')

# ============================================================================
# LOAD COGS
# ============================================================================
async def load_extensions():
    """Load all cog extensions."""
    extensions = [
        'cogs.database',
        'cogs.unbelievaboat',
        'cogs.economy',
        'cogs.admin',
        'cogs.transfer',
        'cogs.broadcast'
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            logger.info(f'Loaded extension: {extension}')
        except Exception as e:
            logger.error(f'Failed to load extension {extension}: {e}')

# ============================================================================
# MAIN
# ============================================================================
async def main():
    """Main entry point."""
    async with bot:
        await load_extensions()
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Bot shutdown requested')
    except Exception as e:
        logger.error(f'Fatal error: {e}')
