import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from .ticket_system import TicketSetupView
from .moderation import ModerationSetupView
from .autorole import AutoroleSetupView

class SetupView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        
    @discord.ui.button(label="Channel Settings", style=discord.ButtonStyle.primary)
    async def setup_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        select = discord.ui.Select(
            placeholder="Choose channel type to configure",
            options=[
                discord.SelectOption(
                    label="Join to Create",
                    description="Configure automatic voice channels system",
                    value="jtc"
                ),
                discord.SelectOption(
                    label="Ticket System",
                    description="Configure ticket system",
                    value="ticket"
                )
            ]
        )
        
        async def select_callback(interaction: discord.Interaction):
            if select.values[0] == "jtc":
                jtc_view = JTCSetupView(self.bot)
                await interaction.response.edit_message(
                    content="Join to Create System Configuration",
                    view=jtc_view
                )
            elif select.values[0] == "ticket":
                ticket_view = TicketSetupView(self.bot)
                await interaction.response.edit_message(
                    content="Ticket System Configuration",
                    view=ticket_view
                )
        
        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.edit_message(view=view)
        
    @discord.ui.button(label="Logs Settings", style=discord.ButtonStyle.primary)
    async def setup_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        select = discord.ui.Select(
            placeholder="Choose log type to configure",
            options=[
                discord.SelectOption(
                    label="Voice Channels",
                    description="Configure voice channels logs",
                    value="voice"
                ),
                discord.SelectOption(
                    label="Tickets",
                    description="Configure tickets logs",
                    value="ticket"
                )
            ]
        )
        
        async def select_callback(interaction: discord.Interaction):
            if select.values[0] == "voice":
                logs_view = VoiceLogsView(self.bot)
                await interaction.response.edit_message(
                    content="Voice Channels Logs Configuration",
                    view=logs_view
                )
            elif select.values[0] == "ticket":
                logs_view = TicketLogsView(self.bot)
                await interaction.response.edit_message(
                    content="Tickets Logs Configuration",
                    view=logs_view
                )
        
        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.edit_message(view=view)

    @discord.ui.button(label="Moderation Settings", style=discord.ButtonStyle.primary)
    async def setup_moderation(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ModerationSetupView(self.bot)
        await interaction.response.edit_message(
            content="Moderation System Configuration",
            view=view
        )

    @discord.ui.button(label="Autorole Settings", style=discord.ButtonStyle.primary)
    async def setup_autorole(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AutoroleSetupView(self.bot)
        await interaction.response.edit_message(
            content="Autorole System Configuration",
            view=view
        )

    @discord.ui.button(label="Forum Settings", style=discord.ButtonStyle.primary)
    async def setup_forum(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ForumSetupModal(self.bot)
        await interaction.response.send_modal(modal)

class VoiceLogsView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.update_buttons()
    
    def update_buttons(self):
        events = self.bot.config["logs"]["voice"]["events"]
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "create":
                    child.style = discord.ButtonStyle.green if events["channel_create"] else discord.ButtonStyle.red
                elif child.custom_id == "delete":
                    child.style = discord.ButtonStyle.green if events["channel_delete"] else discord.ButtonStyle.red
                elif child.custom_id == "rename":
                    child.style = discord.ButtonStyle.green if events["channel_rename"] else discord.ButtonStyle.red
    
    @discord.ui.button(label="Channel Creation", custom_id="create")
    async def toggle_create(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.config["logs"]["voice"]["events"]["channel_create"] = not self.bot.config["logs"]["voice"]["events"]["channel_create"]
        self.bot.save_config()
        self.update_buttons()
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="Channel Deletion", custom_id="delete")
    async def toggle_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.config["logs"]["voice"]["events"]["channel_delete"] = not self.bot.config["logs"]["voice"]["events"]["channel_delete"]
        self.bot.save_config()
        self.update_buttons()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Channel Rename", custom_id="rename")
    async def toggle_rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.config["logs"]["voice"]["events"]["channel_rename"] = not self.bot.config["logs"]["voice"]["events"]["channel_rename"]
        self.bot.save_config()
        self.update_buttons()
        await interaction.response.edit_message(view=self)

class JTCSetupView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        
    @discord.ui.button(label="Set Category", style=discord.ButtonStyle.primary)
    async def setup_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = JTCCategoryModal(self.bot)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="Set JTC Channel", style=discord.ButtonStyle.primary)
    async def setup_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.bot.config["jtc"]["category_id"]:
            await interaction.response.send_message("❌ Please set up the category first!", ephemeral=True)
            return
        modal = JTCChannelModal(self.bot)
        await interaction.response.send_modal(modal)

class JTCCategoryModal(discord.ui.Modal, title="Configuration de la catégorie JTC"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        
    category = discord.ui.TextInput(
        label="ID de la catégorie",
        placeholder="Entrez l'ID de la catégorie pour les salons vocaux",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            category_id = int(self.category.value)
            category = interaction.guild.get_channel(category_id)
            if not category or not isinstance(category, discord.CategoryChannel):
                await interaction.response.send_message("❌ Catégorie invalide!", ephemeral=True)
                return
                
            self.bot.config["jtc"]["category_id"] = category_id
            self.bot.save_config()
            await interaction.response.send_message(f"✅ Catégorie configurée: {category.name}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ ID invalide!", ephemeral=True)

class JTCChannelModal(discord.ui.Modal, title="Configuration du salon JTC"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        
    channel_name = discord.ui.TextInput(
        label="Nom du salon",
        placeholder="➕ Créer un salon",
        required=True,
        default="➕ Créer un salon"
    )
    
    user_limit = discord.ui.TextInput(
        label="Limite d'utilisateurs (0 = pas de limite)",
        placeholder="0",
        required=True,
        default="0"
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_limit = int(self.user_limit.value)
            if user_limit < 0:
                raise ValueError
                
            category_id = self.bot.config["jtc"]["category_id"]
            category = interaction.guild.get_channel(category_id)
            
            # Créer le salon JTC
            channel = await interaction.guild.create_voice_channel(
                name=self.channel_name.value,
                category=category
            )
            
            self.bot.config["jtc"]["channel_id"] = channel.id
            self.bot.config["jtc"]["channel_name"] = self.channel_name.value
            self.bot.config["jtc"]["user_limit"] = user_limit
            self.bot.save_config()
            
            await interaction.response.send_message(
                f"✅ Salon JTC configuré!\nNom: {self.channel_name.value}\nLimite: {user_limit} utilisateurs",
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message("❌ Limite d'utilisateurs invalide!", ephemeral=True)

class TicketLogsView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.update_buttons()
    
    def update_buttons(self):
        events = self.bot.config["logs"]["ticket"]["events"]
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "create":
                    child.style = discord.ButtonStyle.green if events["ticket_create"] else discord.ButtonStyle.red
                elif child.custom_id == "close":
                    child.style = discord.ButtonStyle.green if events["ticket_close"] else discord.ButtonStyle.red
                elif child.custom_id == "delete":
                    child.style = discord.ButtonStyle.green if events["ticket_delete"] else discord.ButtonStyle.red
    
    @discord.ui.button(label="Ticket Creation", custom_id="create")
    async def toggle_create(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.config["logs"]["ticket"]["events"]["ticket_create"] = not self.bot.config["logs"]["ticket"]["events"]["ticket_create"]
        self.bot.save_config()
        self.update_buttons()
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="Ticket Close/Reopen", custom_id="close")
    async def toggle_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.config["logs"]["ticket"]["events"]["ticket_close"] = not self.bot.config["logs"]["ticket"]["events"]["ticket_close"]
        self.bot.save_config()
        self.update_buttons()
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="Ticket Deletion", custom_id="delete")
    async def toggle_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.config["logs"]["ticket"]["events"]["ticket_delete"] = not self.bot.config["logs"]["ticket"]["events"]["ticket_delete"]
        self.bot.save_config()
        self.update_buttons()
        await interaction.response.edit_message(view=self)

class ForumSetupModal(discord.ui.Modal, title="Configuration du Forum"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        
    forum_id = discord.ui.TextInput(
        label="ID du Forum",
        placeholder="Entrez l'ID du forum pour les transferts",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            forum_id = int(self.forum_id.value)
            forum = interaction.guild.get_channel(forum_id)
            if not forum or not isinstance(forum, discord.ForumChannel):
                await interaction.response.send_message("❌ Forum invalide!", ephemeral=True)
                return
                
            if "forum" not in self.bot.config:
                self.bot.config["forum"] = {}
            
            self.bot.config["forum"]["channel_id"] = forum_id
            self.bot.config["forum"]["links"] = self.bot.config["forum"].get("links", {})
            self.bot.save_config()
            
            await interaction.response.send_message(f"✅ Forum configuré: {forum.name}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ ID invalide!", ephemeral=True)

class VoiceCreator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(
        name="setup",
        description="Configure bot settings"
    )
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        view = SetupView(self.bot)
        await interaction.response.send_message(
            "🔧 Bot Configuration",
            view=view,
            ephemeral=True
        )
    
    def is_channel_owner(self, member: discord.Member, channel_id: str) -> bool:
        """Vérifie si le membre est le propriétaire du salon"""
        return str(channel_id) in self.bot.config["jtc"]["created_channels"] and \
               self.bot.config["jtc"]["created_channels"][str(channel_id)] == member.id

    @app_commands.command(
        name="voc-mute",
        description="Mute users in your voice channel"
    )
    @app_commands.describe(user="The user to mute (leave empty to mute everyone)")
    async def voc_mute(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel!", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        if not self.is_channel_owner(interaction.user, channel.id):
            await interaction.response.send_message("❌ You don't own this channel!", ephemeral=True)
            return

        if user:
            if user not in channel.members:
                await interaction.response.send_message("❌ This user is not in your channel!", ephemeral=True)
                return
            await user.edit(mute=True)
            await interaction.response.send_message(f"✅ {user.mention} has been muted", ephemeral=True)
        else:
            for member in channel.members:
                if member != interaction.user:  # Ne pas mute le propriétaire
                    await member.edit(mute=True)
            await interaction.response.send_message("✅ All users have been muted", ephemeral=True)

    @app_commands.command(
        name="voc-kick",
        description="Kick a user from your voice channel"
    )
    @app_commands.describe(user="The user to kick")
    async def voc_kick(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel!", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        if not self.is_channel_owner(interaction.user, channel.id):
            await interaction.response.send_message("❌ You don't own this channel!", ephemeral=True)
            return

        if user not in channel.members:
            await interaction.response.send_message("❌ This user is not in your channel!", ephemeral=True)
            return

        await user.move_to(None)
        await interaction.response.send_message(f"✅ {user.mention} has been kicked from the channel", ephemeral=True)

    @app_commands.command(
        name="voc-ban",
        description="Ban a user from your voice channel"
    )
    @app_commands.describe(user="The user to ban")
    async def voc_ban(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel!", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        if not self.is_channel_owner(interaction.user, channel.id):
            await interaction.response.send_message("❌ You don't own this channel!", ephemeral=True)
            return

        # Ajouter l'utilisateur à la liste des bannis du salon
        channel_id = str(channel.id)
        if "banned_users" not in self.bot.config["jtc"]:
            self.bot.config["jtc"]["banned_users"] = {}
        if channel_id not in self.bot.config["jtc"]["banned_users"]:
            self.bot.config["jtc"]["banned_users"][channel_id] = []
        
        if user.id in self.bot.config["jtc"]["banned_users"][channel_id]:
            await interaction.response.send_message("❌ This user is already banned!", ephemeral=True)
            return

        self.bot.config["jtc"]["banned_users"][channel_id].append(user.id)
        self.bot.save_config()

        if user in channel.members:
            await user.move_to(None)
        
        await interaction.response.send_message(f"✅ {user.mention} has been banned from the channel", ephemeral=True)

    @app_commands.command(
        name="voc-rename",
        description="Rename your voice channel"
    )
    @app_commands.describe(name="The new name for the channel")
    async def voc_rename(self, interaction: discord.Interaction, name: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel!", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        if not self.is_channel_owner(interaction.user, channel.id):
            await interaction.response.send_message("❌ You don't own this channel!", ephemeral=True)
            return

        old_name = channel.name
        await channel.edit(name=name)
        
        # Log si activé
        if self.bot.config["logs"]["voice"]["events"]["channel_rename"]:
            self.bot.log_to_file(
                "VOICE_RENAME",
                f"Channel renamed from '{old_name}' to '{name}' by {interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id})"
            )
        
        await interaction.response.send_message(f"✅ Channel renamed to: {name}", ephemeral=True)

    @app_commands.command(
        name="voc-limit",
        description="Set user limit for your voice channel"
    )
    @app_commands.describe(limit="The maximum number of users (0 for no limit)")
    async def voc_limit(self, interaction: discord.Interaction, limit: int):
        if limit < 0:
            await interaction.response.send_message("❌ The limit cannot be negative!", ephemeral=True)
            return

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel!", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        if not self.is_channel_owner(interaction.user, channel.id):
            await interaction.response.send_message("❌ You don't own this channel!", ephemeral=True)
            return

        await channel.edit(user_limit=limit)
        limit_text = "no limit" if limit == 0 else str(limit)
        await interaction.response.send_message(f"✅ User limit set to: {limit_text}", ephemeral=True)

    @app_commands.command(
        name="voc-close",
        description="Close your voice channel to new users"
    )
    async def voc_close(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel!", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        if not self.is_channel_owner(interaction.user, channel.id):
            await interaction.response.send_message("❌ You don't own this channel!", ephemeral=True)
            return

        # Définir les permissions pour empêcher les nouveaux utilisateurs de rejoindre
        await channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("✅ Channel is now closed to new users", ephemeral=True)

    @app_commands.command(
        name="voc-open",
        description="Open your voice channel to new users"
    )
    async def voc_open(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel!", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        if not self.is_channel_owner(interaction.user, channel.id):
            await interaction.response.send_message("❌ You don't own this channel!", ephemeral=True)
            return

        # Réinitialiser les permissions
        await channel.set_permissions(interaction.guild.default_role, connect=None)
        await interaction.response.send_message("✅ Channel is now open to new users", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        config = self.bot.config["jtc"]
        
        # Vérifier si l'utilisateur rejoint le salon JTC
        if after.channel and after.channel.id == config["channel_id"]:
            # Créer un nouveau salon
            category = after.channel.category
            new_channel = await category.create_voice_channel(
                name=f"🔊 Channel of {member.display_name}",
                user_limit=config["user_limit"]
            )
            
            # Déplacer l'utilisateur
            await member.move_to(new_channel)
            
            # Sauvegarder le salon créé
            config["created_channels"][str(new_channel.id)] = member.id
            self.bot.save_config()
            
            # Log si activé
            if self.bot.config["logs"]["voice"]["events"]["channel_create"]:
                self.bot.log_to_file(
                    "VOICE_CREATE",
                    f"Channel '{new_channel.name}' created by {member.name}#{member.discriminator} (ID: {member.id})"
                )
        
        # Vérifier si un salon est vide pour le supprimer
        if before.channel and str(before.channel.id) in config["created_channels"]:
            if len(before.channel.members) == 0:
                try:
                    channel_name = before.channel.name
                    channel_id = str(before.channel.id)
                    
                    # Vérifier si le salon existe toujours
                    channel = member.guild.get_channel(before.channel.id)
                    if channel:
                        await channel.delete()
                    
                    # Supprimer de la configuration dans tous les cas
                    del config["created_channels"][channel_id]
                    self.bot.save_config()
                    
                    # Log si activé
                    if self.bot.config["logs"]["voice"]["events"]["channel_delete"]:
                        self.bot.log_to_file(
                            "VOICE_DELETE",
                            f"Channel '{channel_name}' was deleted (empty)"
                        )
                except discord.NotFound:
                    # Si le salon n'existe plus, on le retire juste de la config
                    del config["created_channels"][str(before.channel.id)]
                    self.bot.save_config()

        # Vérifier si l'utilisateur est banni du salon qu'il essaie de rejoindre
        if after.channel and str(after.channel.id) in self.bot.config["jtc"].get("banned_users", {}):
            if member.id in self.bot.config["jtc"]["banned_users"][str(after.channel.id)]:
                await member.move_to(None)
                try:
                    await member.send(f"You are banned from this voice channel!")
                except discord.Forbidden:
                    pass

async def setup(bot):
    await bot.add_cog(VoiceCreator(bot)) 