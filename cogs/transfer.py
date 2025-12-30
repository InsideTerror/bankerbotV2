import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import List

logger = logging.getLogger('BankerBot.Transfer')

class TransferCommands(commands.Cog):
    """Currency transfer commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def get_db(self):
        return self.bot.get_cog('Database')
    
    def get_unb(self):
        return self.bot.get_cog('UnbelievaBoat')
    
    # ========================================================================
    # TRANSFER COMMAND
    # ========================================================================
    
    @app_commands.command(name="transfer", description="Transfer currency between servers")
    @app_commands.describe(
        target_server="The server to transfer TO",
        source_server="The server to transfer FROM",
        amount="Amount to transfer (in source currency)",
        wallet_type="Which wallet to use (cash or bank)"
    )
    async def transfer(
        self,
        interaction: discord.Interaction,
        target_server: str,
        source_server: str,
        amount: float,
        wallet_type: str
    ):
        """Transfer currency between approved economies."""
        await interaction.response.defer(ephemeral=True)
        
        db = self.get_db()
        unb = self.get_unb()
        
        if not db or not unb:
            await interaction.followup.send(
                "❌ Bot services not available.",
                ephemeral=True
            )
            return
        
        # Validate wallet type
        wallet_type = wallet_type.lower()
        if wallet_type not in ['cash', 'bank']:
            await interaction.followup.send(
                "❌ Invalid wallet type. Use 'cash' or 'bank'.",
                ephemeral=True
            )
            return
        
        # Validate amount
        min_amount = self.bot.config['min_transfer_amount']
        max_amount = self.bot.config['max_transfer_amount']
        
        if amount < min_amount or amount > max_amount:
            await interaction.followup.send(
                f"❌ Transfer amount must be between {min_amount} and {max_amount}.",
                ephemeral=True
            )
            return
        
        # Get all approved economies
        economies = await db.get_all_economies('approved')
        
        # Find source and target economies (by name, case-insensitive)
        source_economy = None
        target_economy = None
        
        for economy in economies:
            if economy['guild_name'].lower() == source_server.lower():
                source_economy = economy
            if economy['guild_name'].lower() == target_server.lower():
                target_economy = economy
        
        if not source_economy:
            await interaction.followup.send(
                f"❌ Source server '{source_server}' not found in global economy.\n"
                f"Use `/economy list` to see approved servers.",
                ephemeral=True
            )
            return
        
        if not target_economy:
            await interaction.followup.send(
                f"❌ Target server '{target_server}' not found in global economy.\n"
                f"Use `/economy list` to see approved servers.",
                ephemeral=True
            )
            return
        
        if source_economy['guild_id'] == target_economy['guild_id']:
            await interaction.followup.send(
                "❌ Source and target servers cannot be the same.",
                ephemeral=True
            )
            return
        
        # Check if user has sufficient balance
        has_balance = await unb.user_has_sufficient_balance(
            source_economy['guild_id'],
            interaction.user.id,
            amount,
            wallet_type
        )
        
        if not has_balance:
            await interaction.followup.send(
                f"❌ Insufficient {wallet_type} balance in {source_economy['guild_name']}.\n"
                f"You need at least {amount} {source_economy['currency_symbol']}",
                ephemeral=True
            )
            return
        
        # Calculate conversion
        # Convert source currency to USD, then USD to target currency
        amount_usd = amount / source_economy['rate_usd']
        target_amount = amount_usd * target_economy['rate_usd']
        
        # Confirmation
        embed = discord.Embed(
            title="💸 Transfer Confirmation",
            description="Please confirm the following transfer:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="From",
            value=f"{source_economy['guild_name']}\n{source_economy['currency_symbol']} {source_economy['currency_name']}",
            inline=True
        )
        embed.add_field(
            name="To",
            value=f"{target_economy['guild_name']}\n{target_economy['currency_symbol']} {target_economy['currency_name']}",
            inline=True
        )
        embed.add_field(name="Wallet", value=wallet_type.capitalize(), inline=True)
        embed.add_field(
            name="You Pay",
            value=f"{amount:,.2f} {source_economy['currency_symbol']}",
            inline=True
        )
        embed.add_field(
            name="You Receive",
            value=f"{target_amount:,.2f} {target_economy['currency_symbol']}",
            inline=True
        )
        embed.add_field(
            name="Exchange Rate",
            value=f"1 {source_economy['currency_symbol']} = {target_economy['rate_usd'] / source_economy['rate_usd']:.4f} {target_economy['currency_symbol']}",
            inline=True
        )
        
        view = ConfirmTransferView(
            self.bot,
            interaction.user.id,
            source_economy,
            target_economy,
            amount,
            target_amount,
            wallet_type
        )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @transfer.autocomplete('source_server')
    async def source_server_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for source server."""
        db = self.get_db()
        if not db:
            return []
        
        economies = await db.get_all_economies('approved')
        
        # Filter by current input
        filtered = [e for e in economies if current.lower() in e['guild_name'].lower()]
        
        return [
            app_commands.Choice(name=e['guild_name'], value=e['guild_name'])
            for e in filtered[:25]
        ]
    
    @transfer.autocomplete('target_server')
    async def target_server_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for target server."""
        db = self.get_db()
        if not db:
            return []
        
        economies = await db.get_all_economies('approved')
        
        # Filter by current input
        filtered = [e for e in economies if current.lower() in e['guild_name'].lower()]
        
        return [
            app_commands.Choice(name=e['guild_name'], value=e['guild_name'])
            for e in filtered[:25]
        ]
    
    @transfer.autocomplete('wallet_type')
    async def wallet_type_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for wallet type."""
        return [
            app_commands.Choice(name="Cash", value="cash"),
            app_commands.Choice(name="Bank", value="bank")
        ]

async def setup(bot):
    await bot.add_cog(TransferCommands(bot))

# ============================================================================
# TRANSFER CONFIRMATION VIEW
# ============================================================================

class ConfirmTransferView(discord.ui.View):
    """View for confirming transfers."""
    
    def __init__(self, bot, user_id: int, source_economy: dict, 
                 target_economy: dict, amount: float, target_amount: float,
                 wallet_type: str):
        super().__init__(timeout=120)
        self.bot = bot
        self.user_id = user_id
        self.source_economy = source_economy
        self.target_economy = target_economy
        self.amount = amount
        self.target_amount = target_amount
        self.wallet_type = wallet_type
    
    @discord.ui.button(label="Confirm Transfer", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This transfer belongs to someone else.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        db = self.bot.get_cog('Database')
        unb = self.bot.get_cog('UnbelievaBoat')
        
        # Double-check balance
        has_balance = await unb.user_has_sufficient_balance(
            self.source_economy['guild_id'],
            interaction.user.id,
            self.amount,
            self.wallet_type
        )
        
        if not has_balance:
            await interaction.followup.send(
                f"❌ Insufficient balance. The transfer has been cancelled.",
                ephemeral=True
            )
            self.stop()
            return
        
        # Perform transfer
        try:
            # Deduct from source
            if self.wallet_type == 'cash':
                source_result = await unb.modify_user_balance(
                    self.source_economy['guild_id'],
                    interaction.user.id,
                    cash_change=-self.amount,
                    reason=f"Transfer to {self.target_economy['guild_name']}"
                )
            else:
                source_result = await unb.modify_user_balance(
                    self.source_economy['guild_id'],
                    interaction.user.id,
                    bank_change=-self.amount,
                    reason=f"Transfer to {self.target_economy['guild_name']}"
                )
            
            if not source_result:
                await interaction.followup.send(
                    "❌ Failed to deduct from source account.",
                    ephemeral=True
                )
                self.stop()
                return
            
            # Add to target
            if self.wallet_type == 'cash':
                target_result = await unb.modify_user_balance(
                    self.target_economy['guild_id'],
                    interaction.user.id,
                    cash_change=self.target_amount,
                    reason=f"Transfer from {self.source_economy['guild_name']}"
                )
            else:
                target_result = await unb.modify_user_balance(
                    self.target_economy['guild_id'],
                    interaction.user.id,
                    bank_change=self.target_amount,
                    reason=f"Transfer from {self.source_economy['guild_name']}"
                )
            
            if not target_result:
                # Rollback: add money back to source
                if self.wallet_type == 'cash':
                    await unb.modify_user_balance(
                        self.source_economy['guild_id'],
                        interaction.user.id,
                        cash_change=self.amount,
                        reason="Transfer rollback"
                    )
                else:
                    await unb.modify_user_balance(
                        self.source_economy['guild_id'],
                        interaction.user.id,
                        bank_change=self.amount,
                        reason="Transfer rollback"
                    )
                
                await interaction.followup.send(
                    "❌ Failed to add to target account. Transfer rolled back.",
                    ephemeral=True
                )
                self.stop()
                return
            
            # Log transfer
            exchange_rate = self.target_economy['rate_usd'] / self.source_economy['rate_usd']
            await db.log_transfer(
                interaction.user.id,
                self.source_economy['guild_id'],
                self.target_economy['guild_id'],
                self.amount,
                self.target_amount,
                self.source_economy['currency_name'],
                self.target_economy['currency_name'],
                self.wallet_type,
                exchange_rate
            )
            
            await db.log_action(
                'transfer',
                interaction.user.id,
                self.source_economy['guild_id'],
                f"Transferred {self.amount} to {self.target_economy['guild_name']}"
            )
            
            # Success message
            embed = discord.Embed(
                title="✅ Transfer Complete!",
                description="Your transfer was successful.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Sent",
                value=f"{self.amount:,.2f} {self.source_economy['currency_symbol']} ({self.source_economy['guild_name']})",
                inline=False
            )
            embed.add_field(
                name="Received",
                value=f"{self.target_amount:,.2f} {self.target_economy['currency_symbol']} ({self.target_economy['guild_name']})",
                inline=False
            )
            embed.add_field(
                name="Wallet",
                value=self.wallet_type.capitalize(),
                inline=True
            )
            
            # Disable buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.edit_original_response(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f'Transfer error: {e}')
            await interaction.followup.send(
                "❌ An error occurred during the transfer. Please contact support.",
                ephemeral=True
            )
        
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This transfer belongs to someone else.",
                ephemeral=True
            )
            return
        
        await interaction.response.send_message("❌ Transfer cancelled.", ephemeral=True)
        self.stop()
