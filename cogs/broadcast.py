import discord
from discord.ext import commands, tasks
import logging
from typing import Optional, Dict
import asyncio
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger('BankerBot.Broadcast')

class BroadcastSystem(commands.Cog):
    """Ticket-based broadcasting system for sending messages to economy servers."""
    
    def __init__(self, bot):
        self.bot = bot
        self.broadcast_messages: Dict[str, int] = {}  # type -> message_id
        self.active_tickets: Dict[int, Dict] = {}  # channel_id -> ticket_data
        self.log_file = Path('broadcast_log.txt')
        self.message_store_file = Path('broadcast_messages.json')
        
        # Load stored message IDs
        self.load_message_ids()
        
        # Start the daily check task
        self.check_broadcast_messages.start()
    
    def cog_unload(self):
        """Cleanup when cog is unloaded."""
        self.check_broadcast_messages.cancel()
        self.save_message_ids()
    
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
    
    def save_message_ids(self):
        """Save broadcast message IDs to file."""
        try:
            with open(self.message_store_file, 'w') as f:
                json.dump(self.broadcast_messages, f)
        except Exception as e:
            logger.error(f'Failed to save message IDs: {e}')
    
    def load_message_ids(self):
        """Load broadcast message IDs from file."""
        try:
            if self.message_store_file.exists():
                with open(self.message_store_file, 'r') as f:
                    self.broadcast_messages = json.load(f)
        except Exception as e:
            logger.error(f'Failed to load message IDs: {e}')
    
    def log_broadcast(self, officer_id: int, officer_name: str, target_type: str, 
                     message: str, recipient_count: int):
        """Log a broadcast to the log file."""
        try:
            timestamp = datetime.utcnow().isoformat()
            log_entry = (
                f"[{timestamp}] Officer: {officer_name} ({officer_id}) | "
                f"Target: {target_type} | Recipients: {recipient_count} | "
                f"Message: {message[:100]}{'...' if len(message) > 100 else ''}\n"
            )
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            logger.info(f'Broadcast logged: {target_type} to {recipient_count} servers')
        except Exception as e:
            logger.error(f'Failed to log broadcast: {e}')
    
    # ========================================================================
    # SETUP BROADCAST BUTTONS
    # ========================================================================
    
    @commands.command(name='setup_broadcast')
    async def setup_broadcast(self, ctx):
        """Setup the broadcast button messages in the World Bank server."""
        # Check if user is owner
        if ctx.author.id != self.bot.config['owner_user_id']:
            await ctx.send("❌ Only the bot owner can use this command.")
            return
        
        # Check if we're in the Central Bank server
        if ctx.guild.id != self.bot.config['central_bank_server_id']:
            await ctx.send("❌ This command can only be used in the Central Bank server.")
            return
        
        channel = ctx.channel
        
        # Create embeds for each broadcast type
        pending_embed = discord.Embed(
            title="📧 Broadcast to Pending Applications",
            description=(
                "Click the button below to open a ticket and send a message to all servers "
                "with **pending** applications.\n\n"
                "Perfect for:\n"
                "• Requesting additional information\n"
                "• Notifying about application reviews\n"
                "• General updates for applicants"
            ),
            color=discord.Color.orange()
        )
        pending_embed.set_footer(text="World Bank Officer only")
        
        approved_embed = discord.Embed(
            title="📧 Broadcast to Approved Servers",
            description=(
                "Click the button below to open a ticket and send a message to all "
                "**approved** servers in the global economy.\n\n"
                "Perfect for:\n"
                "• Policy updates\n"
                "• New feature announcements\n"
                "• Economy-wide notifications"
            ),
            color=discord.Color.green()
        )
        approved_embed.set_footer(text="World Bank Officer only")
        
        all_economy_embed = discord.Embed(
            title="📧 Broadcast to All Economy Servers",
            description=(
                "Click the button below to open a ticket and send a message to "
                "**all servers** in the economy system (pending, approved, and rejected).\n\n"
                "Perfect for:\n"
                "• Economy system announcements\n"
                "• Application process updates\n"
                "• Important policy changes"
            ),
            color=discord.Color.blue()
        )
        all_economy_embed.set_footer(text="World Bank Officer only")
        
        all_guilds_embed = discord.Embed(
            title="📧 Broadcast to ALL Bot Servers",
            description=(
                "Click the button below to open a ticket and send a message to "
                "**every server the bot is in**, regardless of economy status.\n\n"
                "Perfect for:\n"
                "• Critical bot maintenance notices\n"
                "• Major feature announcements\n"
                "• Emergency updates\n\n"
                "⚠️ **Use sparingly** - This reaches ALL servers!"
            ),
            color=discord.Color.red()
        )
        all_guilds_embed.set_footer(text="World Bank Officer only • Use with caution")
        
        # Send messages with buttons
        pending_view = BroadcastButtonView(self, 'pending')
        approved_view = BroadcastButtonView(self, 'approved')
        all_economy_view = BroadcastButtonView(self, 'all_economy')
        all_guilds_view = BroadcastButtonView(self, 'all_guilds')
        
        pending_msg = await channel.send(embed=pending_embed, view=pending_view)
        approved_msg = await channel.send(embed=approved_embed, view=approved_view)
        all_economy_msg = await channel.send(embed=all_economy_embed, view=all_economy_view)
        all_guilds_msg = await channel.send(embed=all_guilds_embed, view=all_guilds_view)
        
        # Store message IDs
        self.broadcast_messages['pending'] = pending_msg.id
        self.broadcast_messages['approved'] = approved_msg.id
        self.broadcast_messages['all_economy'] = all_economy_msg.id
        self.broadcast_messages['all_guilds'] = all_guilds_msg.id
        self.save_message_ids()
        
        await ctx.send(
            f"✅ Broadcast system setup complete!\n\n"
            f"**Pending Applications:** {pending_msg.jump_url}\n"
            f"**Approved Servers:** {approved_msg.jump_url}\n"
            f"**All Economy Servers:** {all_economy_msg.jump_url}\n"
            f"**ALL Bot Servers:** {all_guilds_msg.jump_url}"
        )
    
    # ========================================================================
    # DAILY CHECK TASK
    # ========================================================================
    
    @tasks.loop(hours=24)
    async def check_broadcast_messages(self):
        """Check if broadcast messages still exist, recreate if deleted."""
        await self.bot.wait_until_ready()
        
        try:
            central_bank = self.bot.get_guild(self.bot.config['central_bank_server_id'])
            if not central_bank:
                return
            
            approval_channel = central_bank.get_channel(self.bot.config['approval_channel_id'])
            if not approval_channel:
                return
            
            for broadcast_type, message_id in list(self.broadcast_messages.items()):
                try:
                    message = await approval_channel.fetch_message(message_id)
                except discord.NotFound:
                    # Message was deleted, recreate it
                    logger.warning(f'Broadcast message for {broadcast_type} was deleted, recreating...')
                    
                    if broadcast_type == 'pending':
                        embed = discord.Embed(
                            title="📧 Broadcast to Pending Applications",
                            description=(
                                "Click the button below to open a ticket and send a message to all servers "
                                "with **pending** applications."
                            ),
                            color=discord.Color.orange()
                        )
                    elif broadcast_type == 'approved':
                        embed = discord.Embed(
                            title="📧 Broadcast to Approved Servers",
                            description=(
                                "Click the button below to open a ticket and send a message to all "
                                "**approved** servers in the global economy."
                            ),
                            color=discord.Color.green()
                        )
                    elif broadcast_type == 'all_economy':
                        embed = discord.Embed(
                            title="📧 Broadcast to All Economy Servers",
                            description=(
                                "Click the button below to open a ticket and send a message to "
                                "**all servers** in the economy system."
                            ),
                            color=discord.Color.blue()
                        )
                    else:  # all_guilds
                        embed = discord.Embed(
                            title="📧 Broadcast to ALL Bot Servers",
                            description=(
                                "Click the button below to open a ticket and send a message to "
                                "**every server the bot is in**."
                            ),
                            color=discord.Color.red()
                        )
                    
                    embed.set_footer(text="World Bank Officer only")
                    view = BroadcastButtonView(self, broadcast_type)
                    new_message = await approval_channel.send(embed=embed, view=view)
                    
                    self.broadcast_messages[broadcast_type] = new_message.id
                    self.save_message_ids()
                    
        except Exception as e:
            logger.error(f'Error in broadcast message check: {e}')
    
    # ========================================================================
    # TICKET CREATION
    # ========================================================================
    
    async def create_ticket(self, interaction: discord.Interaction, broadcast_type: str):
        """Create a broadcast ticket channel."""
        guild = interaction.guild
        
        # Create ticket channel
        category = None
        for cat in guild.categories:
            if 'broadcast' in cat.name.lower() or 'ticket' in cat.name.lower():
                category = cat
                break
        
        # If no category exists, create one
        if not category:
            category = await guild.create_category("📢 Broadcast Tickets")
        
        # Create channel
        channel_name = f"broadcast-{broadcast_type}-{interaction.user.name}"[:100]
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                embed_links=True,
                attach_files=True
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                embed_links=True,
                manage_channels=True
            )
        }
        
        ticket_channel = await category.create_text_channel(
            channel_name,
            overwrites=overwrites
        )
        
        # Store ticket data
        self.active_tickets[ticket_channel.id] = {
            'type': broadcast_type,
            'officer_id': interaction.user.id,
            'officer_name': str(interaction.user),
            'created_at': datetime.utcnow().isoformat(),
            'message_content': None,
            'awaiting_confirmation': False
        }
        
        # Get recipient count
        db = self.get_db()
        
        if broadcast_type == 'all_guilds':
            recipient_count = len(self.bot.guilds)
            recipients_desc = "ALL servers the bot is in"
        elif broadcast_type == 'all_economy':
            recipients = await db.get_all_economies()
            recipient_count = len(recipients)
            recipients_desc = "All economy servers (pending, approved, rejected)"
        else:
            recipients = await db.get_all_economies(broadcast_type)
            recipient_count = len(recipients)
            recipients_desc = f"{broadcast_type.capitalize()} servers"
        
        # Send welcome message
        embed = discord.Embed(
            title=f"📧 Broadcast Ticket: {broadcast_type.replace('_', ' ').title()}",
            description=(
                f"Welcome to your broadcast ticket!\n\n"
                f"**Target:** {recipients_desc}\n"
                f"**Recipients:** {recipient_count} server(s)\n\n"
                f"**Instructions:**\n"
                f"1. Type your message in this channel\n"
                f"2. The bot will ask you to confirm\n"
                f"3. Once confirmed, your message will be sent to all target servers\n\n"
                f"Type your message now:"
            ),
            color=discord.Color.blue()
        )
        
        if broadcast_type == 'all_guilds':
            embed.add_field(
                name="⚠️ Warning",
                value="This will message EVERY server the bot is in, including those not in the economy!",
                inline=False
            )
        
        embed.set_footer(text="Use !close_ticket to cancel and close this ticket")
        
        await ticket_channel.send(embed=embed)
        
        return ticket_channel
    
    # ========================================================================
    # MESSAGE LISTENER
    # ========================================================================
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages in ticket channels."""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Check if this is a ticket channel
        if message.channel.id not in self.active_tickets:
            return
        
        ticket_data = self.active_tickets[message.channel.id]
        
        # If already awaiting confirmation, ignore new messages
        if ticket_data['awaiting_confirmation']:
            return
        
        # Store the message
        ticket_data['message_content'] = message.content
        ticket_data['awaiting_confirmation'] = True
        
        # Get recipients
        db = self.get_db()
        broadcast_type = ticket_data['type']
        
        if broadcast_type == 'all_guilds':
            # Get ALL guilds bot is in
            recipients = [
                {'guild_id': guild.id, 'guild_name': guild.name, 'status': 'bot_member'}
                for guild in self.bot.guilds
            ]
        elif broadcast_type == 'all_economy':
            recipients = await db.get_all_economies()
        else:
            recipients = await db.get_all_economies(broadcast_type)
        
        # Send confirmation
        embed = discord.Embed(
            title="✅ Confirm Broadcast",
            description="Please confirm that you want to send this message:",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Target",
            value=broadcast_type.replace('_', ' ').title(),
            inline=True
        )
        embed.add_field(
            name="Recipients",
            value=f"{len(recipients)} server(s)",
            inline=True
        )
        embed.add_field(
            name="Message",
            value=message.content[:1000] + ("..." if len(message.content) > 1000 else ""),
            inline=False
        )
        
        # List some recipient servers
        server_list = "\n".join([
            f"• {r['guild_name']}"
            for r in recipients[:10]
        ])
        if len(recipients) > 10:
            server_list += f"\n*...and {len(recipients) - 10} more*"
        
        embed.add_field(
            name="Recipient Servers",
            value=server_list,
            inline=False
        )
        
        if broadcast_type == 'all_guilds':
            embed.add_field(
                name="⚠️ Warning",
                value="This includes servers NOT in the economy system!",
                inline=False
            )
        
        view = ConfirmBroadcastView(self, message.channel.id, recipients)
        await message.channel.send(embed=embed, view=view)
    
    # ========================================================================
    # SEND BROADCAST
    # ========================================================================
    
    async def send_broadcast(self, channel_id: int, recipients: list):
        """Send the broadcast message to all recipients."""
        if channel_id not in self.active_tickets:
            return False, "Ticket not found"
        
        ticket_data = self.active_tickets[channel_id]
        message_content = ticket_data['message_content']
        broadcast_type = ticket_data['type']
        
        ticket_channel = self.bot.get_channel(channel_id)
        if not ticket_channel:
            return False, "Ticket channel not found"
        
        # Send status message
        status_embed = discord.Embed(
            title="📤 Sending Broadcast...",
            description=f"Sending to {len(recipients)} servers...",
            color=discord.Color.blue()
        )
        status_message = await ticket_channel.send(embed=status_embed)
        
        # Send to each server
        sent_count = 0
        failed_count = 0
        failed_servers = []
        
        for recipient in recipients:
            try:
                guild = self.bot.get_guild(recipient['guild_id'])
                if not guild:
                    failed_count += 1
                    failed_servers.append(f"{recipient['guild_name']} (Bot not in server)")
                    continue
                
                # Try to find a suitable channel
                target_channel = None
                
                # Try common channel names first
                for channel_name in ['general', 'announcements', 'economy', 'updates']:
                    for channel in guild.text_channels:
                        if channel_name in channel.name.lower():
                            if channel.permissions_for(guild.me).send_messages:
                                target_channel = channel
                                break
                    if target_channel:
                        break
                
                # If no common channel found, use first available
                if not target_channel:
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            target_channel = channel
                            break
                
                if not target_channel:
                    failed_count += 1
                    failed_servers.append(f"{recipient['guild_name']} (No accessible channel)")
                    continue
                
                # Send message
                broadcast_embed = discord.Embed(
                    title="📢 Message from World Bank",
                    description=message_content,
                    color=discord.Color.blue(),
                    timestamp=discord.utils.utcnow()
                )
                broadcast_embed.set_footer(text="BankerBot Global Economy System")
                
                await target_channel.send(embed=broadcast_embed)
                sent_count += 1
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f'Failed to send to {recipient["guild_name"]}: {e}')
                failed_count += 1
                failed_servers.append(f"{recipient['guild_name']} (Error: {str(e)[:50]})")
        
        # Log the broadcast
        self.log_broadcast(
            ticket_data['officer_id'],
            ticket_data['officer_name'],
            broadcast_type,
            message_content,
            sent_count
        )
        
        # Update status message
        result_embed = discord.Embed(
            title="✅ Broadcast Complete",
            color=discord.Color.green()
        )
        result_embed.add_field(name="Sent", value=str(sent_count), inline=True)
        result_embed.add_field(name="Failed", value=str(failed_count), inline=True)
        
        if failed_servers and len(failed_servers) <= 10:
            result_embed.add_field(
                name="Failed Servers",
                value="\n".join(failed_servers),
                inline=False
            )
        elif failed_servers:
            result_embed.add_field(
                name="Failed Servers",
                value=f"{len(failed_servers)} servers failed. Check logs for details.",
                inline=False
            )
        
        await status_message.edit(embed=result_embed)
        
        # Close the ticket after 30 seconds
        await asyncio.sleep(30)
        try:
            await ticket_channel.delete(reason="Broadcast completed")
            del self.active_tickets[channel_id]
        except:
            pass
        
        return True, f"Sent to {sent_count}/{len(recipients)} servers"
    
    # ========================================================================
    # SPECIFIC SERVER BROADCAST (Command-based)
    # ========================================================================
    
    @commands.command(name='broadcast_server')
    async def broadcast_server(self, ctx, server_name: str, *, message: str):
        """
        Broadcast a message to a specific server.
        Usage: !broadcast_server "Server Name" Your message here
        """
        # Check permissions
        if not await self.is_officer_or_owner(ctx.author.id):
            await ctx.send("❌ You are not authorized to use this command.")
            return
        
        db = self.get_db()
        
        # Find the server
        all_economies = await db.get_all_economies()
        target_economy = None
        
        for economy in all_economies:
            if economy['guild_name'].lower() == server_name.lower():
                target_economy = economy
                break
        
        if not target_economy:
            await ctx.send(f"❌ Server '{server_name}' not found in the economy system.")
            return
        
        # Get the guild
        guild = self.bot.get_guild(target_economy['guild_id'])
        if not guild:
            await ctx.send(f"❌ Bot is not in the server '{server_name}'.")
            return
        
        # Find a channel
        target_channel = None
        for channel_name in ['general', 'announcements', 'economy', 'updates']:
            for channel in guild.text_channels:
                if channel_name in channel.name.lower():
                    if channel.permissions_for(guild.me).send_messages:
                        target_channel = channel
                        break
            if target_channel:
                break
        
        if not target_channel:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    target_channel = channel
                    break
        
        if not target_channel:
            await ctx.send(f"❌ No accessible channel found in '{server_name}'.")
            return
        
        # Send the message
        try:
            broadcast_embed = discord.Embed(
                title="📢 Message from World Bank",
                description=message,
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            broadcast_embed.set_footer(text="BankerBot Global Economy System")
            
            await target_channel.send(embed=broadcast_embed)
            
            # Log it
            self.log_broadcast(
                ctx.author.id,
                str(ctx.author),
                f"specific: {server_name}",
                message,
                1
            )
            
            await ctx.send(f"✅ Message sent to **{server_name}** in {target_channel.mention}")
            
        except Exception as e:
            await ctx.send(f"❌ Failed to send message: {e}")
    
    # ========================================================================
    # CLOSE TICKET COMMAND
    # ========================================================================
    
    @commands.command(name='close_ticket')
    async def close_ticket(self, ctx):
        """Close the current broadcast ticket."""
        if ctx.channel.id not in self.active_tickets:
            await ctx.send("❌ This is not a broadcast ticket channel.")
            return
        
        ticket_data = self.active_tickets[ctx.channel.id]
        
        if ctx.author.id != ticket_data['officer_id']:
            await ctx.send("❌ Only the officer who created this ticket can close it.")
            return
        
        await ctx.send("🗑️ Closing ticket in 3 seconds...")
        await asyncio.sleep(3)
        
        del self.active_tickets[ctx.channel.id]
        await ctx.channel.delete(reason="Ticket closed by officer")

async def setup(bot):
    await bot.add_cog(BroadcastSystem(bot))

# ============================================================================
# VIEWS AND BUTTONS
# ============================================================================

class BroadcastButtonView(discord.ui.View):
    """Persistent view for broadcast buttons."""
    
    def __init__(self, cog, broadcast_type: str):
        super().__init__(timeout=None)
        self.cog = cog
        self.broadcast_type = broadcast_type
    
    @discord.ui.button(
        label="Create Broadcast Ticket",
        style=discord.ButtonStyle.primary,
        emoji="📧",
        custom_id="create_broadcast_ticket"
    )
    async def create_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user is an officer
        if not await self.cog.is_officer_or_owner(interaction.user.id):
            await interaction.response.send_message(
                "❌ Only World Bank Officers can create broadcast tickets.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Create the ticket
        ticket_channel = await self.cog.create_ticket(interaction, self.broadcast_type)
        
        await interaction.followup.send(
            f"✅ Broadcast ticket created: {ticket_channel.mention}",
            ephemeral=True
        )

class ConfirmBroadcastView(discord.ui.View):
    """View for confirming broadcast."""
    
    def __init__(self, cog, channel_id: int, recipients: list):
        super().__init__(timeout=300)
        self.cog = cog
        self.channel_id = channel_id
        self.recipients = recipients
    
    @discord.ui.button(label="Confirm & Send", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user is the ticket owner
        if self.channel_id not in self.cog.active_tickets:
            await interaction.response.send_message("❌ Ticket not found.", ephemeral=True)
            return
        
        ticket_data = self.cog.active_tickets[self.channel_id]
        if interaction.user.id != ticket_data['officer_id']:
            await interaction.response.send_message(
                "❌ Only the ticket owner can confirm.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        
        # Send the broadcast
        success, message = await self.cog.send_broadcast(self.channel_id, self.recipients)
        
        if not success:
            await interaction.followup.send(f"❌ Broadcast failed: {message}")
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user is the ticket owner
        if self.channel_id not in self.cog.active_tickets:
            await interaction.response.send_message("❌ Ticket not found.", ephemeral=True)
            return
        
        ticket_data = self.cog.active_tickets[self.channel_id]
        if interaction.user.id != ticket_data['officer_id']:
            await interaction.response.send_message(
                "❌ Only the ticket owner can cancel.",
                ephemeral=True
            )
            return
        
        # Reset awaiting confirmation
        ticket_data['awaiting_confirmation'] = False
        ticket_data['message_content'] = None
        
        await interaction.response.send_message("❌ Broadcast cancelled. You can type a new message.", ephemeral=True)
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
