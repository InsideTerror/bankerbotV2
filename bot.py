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
DISCORD_TOKEN = "YOUR_DISCORD_BOT_TOKEN"  # Replace with your discord bot's token
UNB_API_KEY = "YOUR_UNB_API_KEY"  # Replace with your Unbelievaboat API key
CENTRAL_BANK_SERVER_ID = "YOUR_CENTRAL_BANK_SERVER_ID"  # Replace with your Central Bank server ID
APPROVAL_CHANNEL_ID = "YOUR_APPROVAL_CHANNEL_ID"  # Replace with approval channel ID
OWNER_USER_ID = "YOUR_OWNER_USER_ID"  # Your Discord user ID for managing officers

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
# NOTE: This bot intentionally uses ONLY non-privileged intents.
# - Message Content Intent is NOT enabled. Officer DM commands (add/remove/list
#   officer, officer help) still work because Discord always includes content
#   for direct messages sent to the bot, regardless of this intent. Broadcast
#   ticket messages are composed via a Modal (see cogs/broadcast.py) instead
#   of being typed and read from on_message, so they don't need it either.
# - Server Members Intent is NOT enabled. The bot never needs a full member
#   list; the few places that looked up a user by ID now fall back to an API
#   fetch (discord.Client.fetch_user) when the user isn't already cached.
# Since there are no more prefix ("!") commands left that rely on reading
# message content, the prefix is effectively unused but harmless to keep.
intents = discord.Intents.default()

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
