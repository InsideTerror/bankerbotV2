import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, List
import re

logger = logging.getLogger('BankerBot.Economy')

class EconomyCommands(commands.Cog):
    """Main economy commands for BankerBot."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def get_db(self):
        """Get database cog."""
        return self.bot.get_cog('Database')
    
    def get_unb(self):
        """Get UnbelievaBoat API cog."""
        return self.bot.get_cog('UnbelievaBoat')
    
    # ========================================================================
    # COMMAND GROUP
    # ========================================================================
    
    economy = app_commands.Group(name="economy", description="Global economy commands")
    
    # ========================================================================
    # OPTIN COMMAND
    # ========================================================================
    
    @economy.command(name="optin", description="Apply to join the global economy")
    @app_commands.describe(
        currency_name="Name of your server's currency",
        rate_usd="Exchange rate: How many of your currency = 1 USD",
        currency_symbol="Symbol for your currency (emoji or UTF-8 character)",
        note="Optional note for your application"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def optin(
        self,
        interaction: discord.Interaction,
        currency_name: str,
        rate_usd: float,
        currency_symbol: str,
        note: Optional[str] = None
    ):
        """Apply for your server to join the global economy."""
        await interaction.response.defer(ephemeral=True)
        
        db = self.get_db()
        unb = self.get_unb()
        
        if not db or not unb:
            await interaction.followup.send(
                "❌ Bot services not available. Please try again later.",
                ephemeral=True
            )
            return
        
        # Validate inputs
        min_rate = self.bot.config['min_exchange_rate']
        max_rate = self.bot.config['max_exchange_rate']
        
        if rate_usd < min_rate or rate_usd > max_rate:
            await interaction.followup.send(
                f"❌ Exchange rate must be between {min_rate} and {max_rate}",
                ephemeral=True
            )
            return
        
        if len(currency_name) > 50:
            await interaction.followup.send(
                "❌ Currency name must be 50 characters or less",
                ephemeral=True
            )
            return
        
        if len(currency_symbol) > 10:
            await interaction.followup.send(
                "❌ Currency symbol must be 10 characters or less",
                ephemeral=True
            )
            return
        
        # Check if server already applied
        existing = await db.get_economy(interaction.guild_id)
        if existing:
            status = existing['status']
            if status == 'approved':
                await interaction.followup.send(
                    "✅ Your server is already part of the global economy!",
                    ephemeral=True
                )
            elif status == 'pending':
                await interaction.followup.send(
                    "⏳ Your application is pending review.",
                    ephemeral=True
                )
            elif status == 'rejected':
                await interaction.followup.send(
                    "❌ Your previous application was rejected. Please contact a World Bank Officer.",
                    ephemeral=True
                )
            return
        
        # Validate UnbelievaBoat API access
        if not await unb.validate_guild_access(interaction.guild_id):
            await interaction.followup.send(
                "❌ **API Access Not Configured**\n\n"
                "Please ensure:\n"
                "1. UnbelievaBoat is added to your server\n"
                "2. You've approved BankerBot's API access at:\n"
                "   https://unbelievaboat.com/applications\n"
                "3. Wait a few minutes for permissions to propagate",
                ephemeral=True
            )
            return
        
        # Add to database
        success = await db.add_economy(
            interaction.guild_id,
            interaction.guild.name,
            currency_name,
            currency_symbol,
            rate_usd,
            interaction.user.id,
            note
        )
        
        if not success:
            await interaction.followup.send(
                "❌ Failed to submit application. Please try again.",
                ephemeral=True
            )
            return
        
        # Log action
        await db.log_action(
            'economy_optin',
            interaction.user.id,
            interaction.guild_id,
            f"Currency: {currency_name}, Rate: {rate_usd}, Symbol: {currency_symbol}"
        )
        
        # Send to approval channel
        try:
            central_bank = self.bot.get_guild(self.bot.config['central_bank_server_id'])
            if central_bank:
                approval_channel = central_bank.get_channel(self.bot.config['approval_channel_id'])
                if approval_channel:
                    embed = discord.Embed(
                        title="🏦 New Economy Application",
                        color=discord.Color.blue(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.add_field(name="Server", value=interaction.guild.name, inline=True)
                    embed.add_field(name="Server ID", value=str(interaction.guild_id), inline=True)
                    embed.add_field(name="Applied By", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
                    embed.add_field(name="Currency", value=f"{currency_symbol} {currency_name}", inline=True)
                    embed.add_field(name="Rate (USD)", value=f"1 USD = {rate_usd} {currency_symbol}", inline=True)
                    if note:
                        embed.add_field(name="Note", value=note, inline=False)
                    
                    view = ApprovalView(self.bot, interaction.guild_id)
                    await approval_channel.send(embed=embed, view=view)
        except Exception as e:
            logger.error(f'Failed to send approval message: {e}')
        
        await interaction.followup.send(
            "✅ **Application Submitted!**\n\n"
            "Your server's application to join the global economy has been submitted.\n"
            "A World Bank Officer will review it shortly.\n\n"
            f"**Currency:** {currency_symbol} {currency_name}\n"
            f"**Exchange Rate:** 1 USD = {rate_usd} {currency_symbol}",
            ephemeral=True
        )
    
    # ========================================================================
    # LIST COMMAND
    # ========================================================================
    
    @economy.command(name="list", description="List all economies in the global market")
    @app_commands.describe(
        status="Filter by status (approved/pending/rejected)"
    )
    async def list_economies(
        self,
        interaction: discord.Interaction,
        status: Optional[str] = None
    ):
        """List all economies in the global market."""
        await interaction.response.defer()
        
        db = self.get_db()
        if not db:
            await interaction.followup.send("❌ Database not available.")
            return
        
        if status and status.lower() not in ['approved', 'pending', 'rejected']:
            await interaction.followup.send(
                "❌ Invalid status. Use: approved, pending, or rejected"
            )
            return
        
        economies = await db.get_all_economies(status.lower() if status else None)
        
        if not economies:
            await interaction.followup.send("No economies found.")
            return
        
        # Group by status
        approved = [e for e in economies if e['status'] == 'approved']
        pending = [e for e in economies if e['status'] == 'pending']
        rejected = [e for e in economies if e['status'] == 'rejected']
        
        embed = discord.Embed(
            title="🌍 Global Economy List",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        
        if not status or status.lower() == 'approved':
            if approved:
                approved_text = "\n".join([
                    f"**{e['guild_name']}**\n"
                    f"└ {e['currency_symbol']} {e['currency_name']} "
                    f"(1 USD = {e['rate_usd']} {e['currency_symbol']})"
                    for e in approved[:10]
                ])
                embed.add_field(
                    name=f"✅ Approved ({len(approved)})",
                    value=approved_text if len(approved) <= 10 else approved_text + f"\n*...and {len(approved) - 10} more*",
                    inline=False
                )
        
        if not status or status.lower() == 'pending':
            if pending:
                pending_text = "\n".join([
                    f"**{e['guild_name']}** - {e['currency_symbol']} {e['currency_name']}"
                    for e in pending[:5]
                ])
                embed.add_field(
                    name=f"⏳ Pending ({len(pending)})",
                    value=pending_text if len(pending) <= 5 else pending_text + f"\n*...and {len(pending) - 5} more*",
                    inline=False
                )
        
        if not status or status.lower() == 'rejected':
            if rejected:
                rejected_text = "\n".join([
                    f"**{e['guild_name']}** - {e['currency_symbol']} {e['currency_name']}"
                    for e in rejected[:5]
                ])
                embed.add_field(
                    name=f"❌ Rejected ({len(rejected)})",
                    value=rejected_text if len(rejected) <= 5 else rejected_text + f"\n*...and {len(rejected) - 5} more*",
                    inline=False
                )
        
        await interaction.followup.send(embed=embed)
    
    # ========================================================================
    # WITHDRAW COMMAND
    # ========================================================================
    
    @economy.command(name="withdraw", description="Remove your server from the global economy")
    @app_commands.checks.has_permissions(administrator=True)
    async def withdraw(self, interaction: discord.Interaction):
        """Withdraw your server from the global economy."""
        await interaction.response.defer(ephemeral=True)
        
        db = self.get_db()
        if not db:
            await interaction.followup.send("❌ Database not available.", ephemeral=True)
            return
        
        economy = await db.get_economy(interaction.guild_id)
        if not economy:
            await interaction.followup.send(
                "❌ Your server is not part of the global economy.",
                ephemeral=True
            )
            return
        
        # Confirmation view
        view = ConfirmWithdrawView(self.bot, interaction.guild_id, interaction.user.id)
        await interaction.followup.send(
            "⚠️ **Confirm Withdrawal**\n\n"
            "Are you sure you want to withdraw from the global economy?\n"
            "You will need to reapply to rejoin.\n\n"
            "This action cannot be undone.",
            view=view,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(EconomyCommands(bot))

# ============================================================================
# VIEWS AND BUTTONS
# ============================================================================

class ApprovalView(discord.ui.View):
    """View for approving/rejecting economy applications."""
    
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="Approve ✅", style=discord.ButtonStyle.green, custom_id="approve")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.bot.get_cog('Database')
        if not db:
            await interaction.response.send_message("❌ Database not available.", ephemeral=True)
            return
        
        # Check if user is an officer
        if not await db.is_officer(interaction.user.id):
            await interaction.response.send_message(
                "❌ You are not authorized to approve applications.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Update status
        success = await db.update_economy_status(self.guild_id, 'approved', interaction.user.id)
        
        if success:
            await db.log_action('economy_approved', interaction.user.id, self.guild_id)
            
            # Update message
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.add_field(
                name="Status",
                value=f"✅ Approved by {interaction.user.mention}",
                inline=False
            )
            
            # Disable buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.message.edit(embed=embed, view=self)
            await interaction.followup.send("✅ Application approved!")
            
            # Notify the guild
            try:
                guild = self.bot.get_guild(self.guild_id)
                if guild:
                    economy = await db.get_economy(self.guild_id)
                    # Try to find a channel to send notification
                    # You might want to store the channel ID during application
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            await channel.send(
                                f"🎉 **Welcome to the Global Economy!**\n\n"
                                f"Your application has been approved!\n"
                                f"Currency: {economy['currency_symbol']} {economy['currency_name']}\n"
                                f"Exchange Rate: 1 USD = {economy['rate_usd']} {economy['currency_symbol']}\n\n"
                                f"Users can now transfer funds using `/economy transfer`"
                            )
                            break
            except Exception as e:
                logger.error(f'Failed to notify guild: {e}')
        else:
            await interaction.followup.send("❌ Failed to approve application.")
    
    @discord.ui.button(label="Reject ❌", style=discord.ButtonStyle.red, custom_id="reject")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.bot.get_cog('Database')
        if not db:
            await interaction.response.send_message("❌ Database not available.", ephemeral=True)
            return
        
        # Check if user is an officer
        if not await db.is_officer(interaction.user.id):
            await interaction.response.send_message(
                "❌ You are not authorized to reject applications.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Update status
        success = await db.update_economy_status(self.guild_id, 'rejected')
        
        if success:
            await db.log_action('economy_rejected', interaction.user.id, self.guild_id)
            
            # Update message
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.red()
            embed.add_field(
                name="Status",
                value=f"❌ Rejected by {interaction.user.mention}",
                inline=False
            )
            
            # Disable buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.message.edit(embed=embed, view=self)
            await interaction.followup.send("❌ Application rejected.")
        else:
            await interaction.followup.send("❌ Failed to reject application.")

class ConfirmWithdrawView(discord.ui.View):
    """View for confirming economy withdrawal."""
    
    def __init__(self, bot, guild_id: int, user_id: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
    
    @discord.ui.button(label="Confirm Withdrawal", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the person who initiated this can confirm.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        db = self.bot.get_cog('Database')
        success = await db.remove_economy(self.guild_id)
        
        if success:
            await db.log_action('economy_withdraw', interaction.user.id, self.guild_id)
            await interaction.followup.send(
                "✅ Your server has been withdrawn from the global economy.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ Failed to withdraw. Please try again.",
                ephemeral=True
            )
        
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the person who initiated this can cancel.",
                ephemeral=True
            )
            return
        
        await interaction.response.send_message("❌ Withdrawal cancelled.", ephemeral=True)
        self.stop()
