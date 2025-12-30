import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, List

logger = logging.getLogger('BankerBot.Admin')

class AdminCommands(commands.Cog):
    """Administrative commands for World Bank Officers."""
    
    def __init__(self, bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name='Add as Officer',
            callback=self.add_officer_context
        )
        self.bot.tree.add_command(self.ctx_menu)
    
    def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)
    
    def get_db(self):
        return self.bot.get_cog('Database')
    
    async def is_officer_or_owner(self, user_id: int) -> bool:
        """Check if user is an officer or the bot owner."""
        if user_id == self.bot.config['owner_user_id']:
            return True
        db = self.get_db()
        if db:
            return await db.is_officer(user_id)
        return False
    
    # ========================================================================
    # KICK COMMAND (Officer only)
    # ========================================================================
    
    @app_commands.command(name="kick_economy", description="[OFFICER] Remove a server from the global economy")
    @app_commands.describe(
        server_name="Name of the server to remove",
        reason="Reason for removal"
    )
    async def kick_economy(
        self,
        interaction: discord.Interaction,
        server_name: str,
        reason: Optional[str] = "No reason provided"
    ):
        """Kick a server from the global economy (Officer only)."""
        # Check permissions
        if not await self.is_officer_or_owner(interaction.user.id):
            await interaction.response.send_message(
                "❌ You are not authorized to use this command.\n"
                "Only World Bank Officers can kick economies.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        db = self.get_db()
        if not db:
            await interaction.followup.send("❌ Database not available.", ephemeral=True)
            return
        
        # Find the economy
        economies = await db.get_all_economies('approved')
        target_economy = None
        
        for economy in economies:
            if economy['guild_name'].lower() == server_name.lower():
                target_economy = economy
                break
        
        if not target_economy:
            await interaction.followup.send(
                f"❌ Server '{server_name}' not found in approved economies.",
                ephemeral=True
            )
            return
        
        # Remove the economy
        success = await db.remove_economy(target_economy['guild_id'])
        
        if success:
            await db.log_action(
                'economy_kicked',
                interaction.user.id,
                target_economy['guild_id'],
                f"Reason: {reason}"
            )
            
            await interaction.followup.send(
                f"✅ Successfully removed **{target_economy['guild_name']}** from the global economy.\n"
                f"Reason: {reason}",
                ephemeral=True
            )
            
            # Try to notify the kicked server
            try:
                guild = self.bot.get_guild(target_economy['guild_id'])
                if guild:
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            embed = discord.Embed(
                                title="⚠️ Removed from Global Economy",
                                description=f"Your server has been removed from the global economy by a World Bank Officer.",
                                color=discord.Color.red()
                            )
                            embed.add_field(name="Reason", value=reason, inline=False)
                            embed.add_field(
                                name="What now?",
                                value="You can reapply using `/economy optin` if you wish to rejoin.",
                                inline=False
                            )
                            await channel.send(embed=embed)
                            break
            except Exception as e:
                logger.error(f'Failed to notify kicked server: {e}')
        else:
            await interaction.followup.send(
                "❌ Failed to remove economy.",
                ephemeral=True
            )
    
    @kick_economy.autocomplete('server_name')
    async def kick_server_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for server name."""
        # Only show autocomplete to officers
        if not await self.is_officer_or_owner(interaction.user.id):
            return []
        
        db = self.get_db()
        if not db:
            return []
        
        economies = await db.get_all_economies('approved')
        filtered = [e for e in economies if current.lower() in e['guild_name'].lower()]
        
        return [
            app_commands.Choice(name=e['guild_name'], value=e['guild_name'])
            for e in filtered[:25]
        ]
    
    # ========================================================================
    # OFFICER MANAGEMENT (Owner only via DM)
    # ========================================================================
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for DMs to add/remove officers."""
        # Only process DMs to the bot
        if not isinstance(message.channel, discord.DMChannel):
            return
        
        if message.author.bot:
            return
        
        # Only owner can manage officers
        if message.author.id != self.bot.config['owner_user_id']:
            return
        
        db = self.get_db()
        if not db:
            return
        
        content = message.content.strip()
        
        # Add officer: "add officer <user_id>"
        if content.lower().startswith('add officer '):
            try:
                user_id = int(content.split()[2])
                success = await db.add_officer(user_id, message.author.id)
                
                if success:
                    await message.reply(f"✅ Added user {user_id} as a World Bank Officer.")
                    await db.log_action('officer_added', message.author.id, details=f"Officer ID: {user_id}")
                else:
                    await message.reply(f"❌ User {user_id} is already an officer or error occurred.")
            except (IndexError, ValueError):
                await message.reply("❌ Invalid format. Use: `add officer <user_id>`")
        
        # Remove officer: "remove officer <user_id>"
        elif content.lower().startswith('remove officer '):
            try:
                user_id = int(content.split()[2])
                success = await db.remove_officer(user_id)
                
                if success:
                    await message.reply(f"✅ Removed user {user_id} from World Bank Officers.")
                    await db.log_action('officer_removed', message.author.id, details=f"Officer ID: {user_id}")
                else:
                    await message.reply(f"❌ User {user_id} is not an officer or error occurred.")
            except (IndexError, ValueError):
                await message.reply("❌ Invalid format. Use: `remove officer <user_id>`")
        
        # List officers: "list officers"
        elif content.lower() == 'list officers':
            officers = await db.get_all_officers()
            
            if not officers:
                await message.reply("No World Bank Officers registered.")
                return
            
            embed = discord.Embed(
                title="👮 World Bank Officers",
                color=discord.Color.blue()
            )
            
            officer_list = []
            for officer in officers:
                user = self.bot.get_user(officer['user_id'])
                if user:
                    officer_list.append(f"• {user.mention} ({user.id})")
                else:
                    officer_list.append(f"• User ID: {officer['user_id']}")
            
            embed.description = "\n".join(officer_list) if officer_list else "None"
            await message.reply(embed=embed)
        
        # Help: "officer help"
        elif content.lower() == 'officer help':
            embed = discord.Embed(
                title="🛠️ Officer Management Commands",
                description="Commands for managing World Bank Officers (Owner only)",
                color=discord.Color.gold()
            )
            embed.add_field(
                name="Add Officer",
                value="`add officer <user_id>`\nGrant officer privileges to a user",
                inline=False
            )
            embed.add_field(
                name="Remove Officer",
                value="`remove officer <user_id>`\nRevoke officer privileges from a user",
                inline=False
            )
            embed.add_field(
                name="List Officers",
                value="`list officers`\nShow all current officers",
                inline=False
            )
            await message.reply(embed=embed)
    
    # ========================================================================
    # CONTEXT MENU (Owner only)
    # ========================================================================
    
    async def add_officer_context(self, interaction: discord.Interaction, user: discord.User):
        """Context menu to add user as officer."""
        if interaction.user.id != self.bot.config['owner_user_id']:
            await interaction.response.send_message(
                "❌ Only the bot owner can add officers.",
                ephemeral=True
            )
            return
        
        db = self.get_db()
        if not db:
            await interaction.response.send_message("❌ Database not available.", ephemeral=True)
            return
        
        success = await db.add_officer(user.id, interaction.user.id)
        
        if success:
            await db.log_action('officer_added', interaction.user.id, details=f"Officer ID: {user.id}")
            await interaction.response.send_message(
                f"✅ Added {user.mention} as a World Bank Officer.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ {user.mention} is already an officer or error occurred.",
                ephemeral=True
            )
    
    # ========================================================================
    # UTILITY COMMANDS
    # ========================================================================
    
    @app_commands.command(name="cleanup_transfers", description="[OFFICER] Clean up old transfer logs")
    @app_commands.describe(
        days="Delete transfers older than this many days (default: 180)"
    )
    async def cleanup_transfers(
        self,
        interaction: discord.Interaction,
        days: int = 180
    ):
        """Clean up old transfer logs (Officer only)."""
        if not await self.is_officer_or_owner(interaction.user.id):
            await interaction.response.send_message(
                "❌ You are not authorized to use this command.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        db = self.get_db()
        if not db:
            await interaction.followup.send("❌ Database not available.", ephemeral=True)
            return
        
        deleted = await db.cleanup_old_transfers(days)
        
        await interaction.followup.send(
            f"✅ Cleaned up {deleted} transfer record(s) older than {days} days.",
            ephemeral=True
        )
        
        await db.log_action(
            'cleanup_transfers',
            interaction.user.id,
            details=f"Deleted {deleted} records older than {days} days"
        )

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
