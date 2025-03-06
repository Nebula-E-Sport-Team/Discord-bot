import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import asyncio
import io

class TicketSetupView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        
    @discord.ui.button(label="Set Message Channel", style=discord.ButtonStyle.primary)
    async def set_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TicketChannelModal(self.bot)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Set Support Role", style=discord.ButtonStyle.primary)
    async def set_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SupportRoleModal(self.bot)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Set Ticket Category", style=discord.ButtonStyle.primary)
    async def set_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TicketCategoryModal(self.bot)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Manage Categories", style=discord.ButtonStyle.primary)
    async def manage_categories(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CategoryManageView(self.bot)
        await interaction.response.edit_message(content="Ticket Categories Management", view=view)
    
    @discord.ui.button(label="Set Transcript Channel", style=discord.ButtonStyle.primary)
    async def set_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TranscriptChannelModal(self.bot)
        await interaction.response.send_modal(modal)

class TicketChannelModal(discord.ui.Modal, title="Ticket Message Channel Setup"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        
    channel_id = discord.ui.TextInput(
        label="Channel ID",
        placeholder="Enter the channel ID for ticket message",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel_id.value)
            channel = interaction.guild.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message("❌ Invalid channel!", ephemeral=True)
                return
            
            self.bot.config["tickets"]["message_channel_id"] = channel_id
            self.bot.save_config()
            
            # Create the ticket message
            view = TicketCreateView(self.bot)
            embed = discord.Embed(
                title="Create a Ticket",
                description="Click the button below to create a ticket",
                color=discord.Color.blue()
            )
            for category, emoji in self.bot.config["tickets"]["categories"].items():
                embed.add_field(name=category, value=f"{emoji}", inline=True)
            
            await channel.send(embed=embed, view=view)
            await interaction.response.send_message("✅ Ticket message channel set!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)

class SupportRoleModal(discord.ui.Modal, title="Support Role Setup"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        
    role_id = discord.ui.TextInput(
        label="Role ID",
        placeholder="Enter the support role ID",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            role_id = int(self.role_id.value)
            role = interaction.guild.get_role(role_id)
            if not role:
                await interaction.response.send_message("❌ Invalid role!", ephemeral=True)
                return
            
            self.bot.config["tickets"]["support_role_id"] = role_id
            self.bot.save_config()
            await interaction.response.send_message(f"✅ Support role set to {role.mention}!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)

class TicketCategoryModal(discord.ui.Modal, title="Ticket Category Setup"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        
    category_id = discord.ui.TextInput(
        label="Category ID",
        placeholder="Enter the category ID for tickets",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            category_id = int(self.category_id.value)
            category = interaction.guild.get_channel(category_id)
            if not category or not isinstance(category, discord.CategoryChannel):
                await interaction.response.send_message("❌ Invalid category!", ephemeral=True)
                return
            
            self.bot.config["tickets"]["category_id"] = category_id
            self.bot.save_config()
            await interaction.response.send_message(f"✅ Ticket category set to: {category.name}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)

class TicketCreateView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user already has an active ticket
        active_tickets = self.bot.config["tickets"]["active_tickets"]
        if str(interaction.user.id) in active_tickets:
            await interaction.response.send_message("❌ You already have an active ticket!", ephemeral=True)
            return
        
        # Create category select
        select = discord.ui.Select(
            placeholder="Select ticket category",
            options=[
                discord.SelectOption(
                    label=category,
                    emoji=emoji,
                    value=category
                ) for category, emoji in self.bot.config["tickets"]["categories"].items()
            ]
        )
        
        async def select_callback(interaction: discord.Interaction):
            category = select.values[0]
            await self.create_ticket_channel(interaction, category)
        
        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.send_message("Please select a category:", view=view, ephemeral=True)
    
    async def create_ticket_channel(self, interaction: discord.Interaction, category: str):
        # Create the channel in the configured category
        category_channel = interaction.guild.get_channel(self.bot.config["tickets"].get("category_id"))
        if not category_channel:
            category_channel = None  # Fallback to no category if not configured
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(self.bot.config["tickets"]["support_role_id"]): 
                discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category_channel,
            overwrites=overwrites
        )
        
        # Save ticket info
        self.bot.config["tickets"]["active_tickets"][str(interaction.user.id)] = {
            "channel_id": channel.id,
            "category": category,
            "status": "waiting_description"
        }
        self.bot.save_config()
        
        # Log de création du ticket
        if self.bot.config["logs"]["ticket"]["events"]["ticket_create"]:
            self.bot.log_to_file(
                "TICKET_CREATE",
                f"Ticket created by {interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id}) "
                f"in category '{category}' - Channel: {channel.name}"
            )
        
        # Send initial message
        embed = discord.Embed(
            title=f"Ticket - {category}",
            description="Please describe your issue. Once you send a message, support will be notified.",
            color=discord.Color.blue()
        )
        
        view = TicketControlView(self.bot)
        message = await channel.send(
            content=f"{interaction.user.mention}",
            embed=embed,
            view=view
        )
        await message.pin()
        
        await interaction.response.send_message(
            f"✅ Ticket created! Check {channel.mention}",
            ephemeral=True
        )

class TicketControlView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verify if user is ticket owner or support
        is_support = interaction.user.get_role(self.bot.config["tickets"]["support_role_id"]) is not None
        is_owner = False
        
        for user_id, ticket in self.bot.config["tickets"]["active_tickets"].items():
            if ticket["channel_id"] == interaction.channel.id:
                is_owner = str(interaction.user.id) == user_id
                break
        
        if not (is_support or is_owner):
            await interaction.response.send_message("❌ You can't close this ticket!", ephemeral=True)
            return
        
        # Remove access for the ticket owner
        for user_id, ticket in self.bot.config["tickets"]["active_tickets"].items():
            if ticket["channel_id"] == interaction.channel.id:
                user = interaction.guild.get_member(int(user_id))
                await interaction.channel.set_permissions(user, read_messages=False)
                
                # Move to closed tickets
                self.bot.config["tickets"]["closed_tickets"][user_id] = ticket
                del self.bot.config["tickets"]["active_tickets"][user_id]
                self.bot.save_config()
                
                # Log de fermeture du ticket
                if self.bot.config["logs"]["ticket"]["events"]["ticket_close"]:
                    self.bot.log_to_file(
                        "TICKET_CLOSE",
                        f"Ticket '{interaction.channel.name}' closed by {interaction.user.name}#{interaction.user.discriminator} "
                        f"(ID: {interaction.user.id}) - Owner: {user.name}#{user.discriminator}"
                    )
                break
        
        # Update the view
        view = ClosedTicketView(self.bot)
        await interaction.message.edit(view=view)
        await interaction.response.send_message("Ticket closed", ephemeral=True)

class ClosedTicketView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="Reopen", style=discord.ButtonStyle.primary, custom_id="reopen_ticket")
    async def reopen_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.get_role(self.bot.config["tickets"]["support_role_id"]):
            await interaction.response.send_message("❌ Only support can reopen tickets!", ephemeral=True)
            return
        
        # Find ticket owner
        for user_id, ticket in self.bot.config["tickets"]["closed_tickets"].items():
            if ticket["channel_id"] == interaction.channel.id:
                user = interaction.guild.get_member(int(user_id))
                await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
                
                # Move back to active tickets
                self.bot.config["tickets"]["active_tickets"][user_id] = ticket
                del self.bot.config["tickets"]["closed_tickets"][user_id]
                self.bot.save_config()
                
                # Log de réouverture du ticket
                if self.bot.config["logs"]["ticket"]["events"]["ticket_close"]:  # On utilise le même événement que la fermeture
                    self.bot.log_to_file(
                        "TICKET_REOPEN",
                        f"Ticket '{interaction.channel.name}' reopened by {interaction.user.name}#{interaction.user.discriminator} "
                        f"(ID: {interaction.user.id}) - Owner: {user.name}#{user.discriminator}"
                    )
                break
        
        # Update the view
        view = TicketControlView(self.bot)
        await interaction.message.edit(view=view)
        await interaction.response.send_message("Ticket reopened", ephemeral=True)
    
    async def create_transcript(self, channel: discord.TextChannel) -> discord.File:
        messages = []
        async for message in channel.history(limit=None, oldest_first=True):
            if message.author.bot and not message.embeds:  # Ignorer les messages du bot sauf les embeds
                continue
            
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if message.embeds:
                for embed in message.embeds:
                    messages.append(f"[{timestamp}] [EMBED] {embed.title}: {embed.description}")
            else:
                messages.append(f"[{timestamp}] {message.author.name}#{message.author.discriminator}: {message.content}")
        
        transcript_text = "\n".join(messages)
        transcript_file = discord.File(
            fp=io.StringIO(transcript_text),
            filename=f"transcript-{channel.name}.txt"
        )
        return transcript_file
    
    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, custom_id="delete_ticket")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.get_role(self.bot.config["tickets"]["support_role_id"]):
            await interaction.response.send_message("❌ Only support can delete tickets!", ephemeral=True)
            return
        
        # Créer la transcription
        transcript_file = await self.create_transcript(interaction.channel)
        
        # Envoyer la transcription si un salon est configuré
        if self.bot.config["tickets"]["transcript_channel_id"]:
            transcript_channel = interaction.guild.get_channel(self.bot.config["tickets"]["transcript_channel_id"])
            if transcript_channel:
                # Trouver les informations du ticket
                ticket_info = None
                ticket_owner = None
                for user_id, ticket in self.bot.config["tickets"]["closed_tickets"].items():
                    if ticket["channel_id"] == interaction.channel.id:
                        ticket_info = ticket
                        ticket_owner = interaction.guild.get_member(int(user_id))
                        break
                
                embed = discord.Embed(
                    title="Ticket Transcript",
                    description=f"Ticket: {interaction.channel.name}\n"
                              f"Category: {ticket_info['category'] if ticket_info else 'Unknown'}\n"
                              f"Owner: {ticket_owner.mention if ticket_owner else 'Unknown'}\n"
                              f"Closed by: {interaction.user.mention}",
                    color=discord.Color.blue(),
                    timestamp=interaction.created_at
                )
                
                await transcript_channel.send(embed=embed, file=transcript_file)
        
        # Log de suppression du ticket
        if self.bot.config["logs"]["ticket"]["events"]["ticket_delete"]:
            for user_id, ticket in self.bot.config["tickets"]["closed_tickets"].items():
                if ticket["channel_id"] == interaction.channel.id:
                    ticket_owner = interaction.guild.get_member(int(user_id))
                    self.bot.log_to_file(
                        "TICKET_DELETE",
                        f"Ticket '{interaction.channel.name}' deleted by {interaction.user.name}#{interaction.user.discriminator} "
                        f"(ID: {interaction.user.id}) - Owner: {ticket_owner.name}#{ticket_owner.discriminator}"
                    )
                    break
        
        await interaction.response.send_message("Channel will be deleted in 5 seconds...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class CategoryManageView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
    
    @discord.ui.button(label="Add Category", style=discord.ButtonStyle.success)
    async def add_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddCategoryModal(self.bot)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Remove Category", style=discord.ButtonStyle.danger)
    async def remove_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Create category select
        select = discord.ui.Select(
            placeholder="Select category to remove",
            options=[
                discord.SelectOption(
                    label=category,
                    emoji=emoji,
                    value=category
                ) for category, emoji in self.bot.config["tickets"]["categories"].items()
            ]
        )
        
        async def select_callback(interaction: discord.Interaction):
            category = select.values[0]
            del self.bot.config["tickets"]["categories"][category]
            self.bot.save_config()
            await interaction.response.send_message(f"✅ Category '{category}' removed!", ephemeral=True)
        
        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.edit_message(view=view)

class AddCategoryModal(discord.ui.Modal, title="Add Ticket Category"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    category_name = discord.ui.TextInput(
        label="Category Name",
        placeholder="e.g. Support, Bug Report",
        required=True
    )
    
    category_emoji = discord.ui.TextInput(
        label="Category Emoji",
        placeholder="e.g. 🎮, 🐛",
        required=True,
        max_length=2
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        name = self.category_name.value
        emoji = self.category_emoji.value
        
        if name in self.bot.config["tickets"]["categories"]:
            await interaction.response.send_message("❌ This category already exists!", ephemeral=True)
            return
        
        self.bot.config["tickets"]["categories"][name] = emoji
        self.bot.save_config()
        
        # Update ticket message if it exists
        if self.bot.config["tickets"]["message_channel_id"]:
            channel = interaction.guild.get_channel(self.bot.config["tickets"]["message_channel_id"])
            if channel:
                view = TicketCreateView(self.bot)
                embed = discord.Embed(
                    title="Create a Ticket",
                    description="Click the button below to create a ticket",
                    color=discord.Color.blue()
                )
                for category, emoji in self.bot.config["tickets"]["categories"].items():
                    embed.add_field(name=category, value=f"{emoji}", inline=True)
                
                await channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(f"✅ Category '{name}' added with emoji {emoji}!", ephemeral=True)

class TranscriptChannelModal(discord.ui.Modal, title="Transcript Channel Setup"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        
    channel_id = discord.ui.TextInput(
        label="Channel ID",
        placeholder="Enter the transcript channel ID",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel_id.value)
            channel = interaction.guild.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message("❌ Invalid channel!", ephemeral=True)
                return
            
            self.bot.config["tickets"]["transcript_channel_id"] = channel_id
            self.bot.save_config()
            await interaction.response.send_message(f"✅ Transcript channel set to {channel.mention}!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Réinitialiser les vues persistantes
        self.bot.add_view(TicketCreateView(bot))
        self.bot.add_view(TicketControlView(bot))
        self.bot.add_view(ClosedTicketView(bot))
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        # Check if message is in a ticket channel
        for user_id, ticket in self.bot.config["tickets"]["active_tickets"].items():
            if ticket["channel_id"] == message.channel.id and ticket["status"] == "waiting_description":
                # Vérifier que c'est bien l'auteur du ticket qui écrit
                if str(message.author.id) != user_id:
                    return
                
                # Update status and notify support
                ticket["status"] = "active"
                self.bot.save_config()
                
                support_role = message.guild.get_role(self.bot.config["tickets"]["support_role_id"])
                await message.channel.send(f"{support_role.mention} New ticket needs attention!")
                break

async def setup(bot):
    await bot.add_cog(TicketSystem(bot)) 