import discord
from discord.ext import commands


class RoleView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        # Créer immédiatement les boutons à partir de la config persistante.
        for role_id, emoji in self.bot.config["autorole"]["roles"].items():
            try:
                self.add_item(RoleButton(role_id, emoji))
            except Exception as e:
                print(f"Erreur création bouton {role_id}: {str(e)}")

    # La méthode interaction_check n'est plus nécessaire car les boutons sont créés dès l'init.
    # Par défaut, interaction_check retourne True.


class RoleButton(discord.ui.Button):
    def __init__(self, role_id: str, emoji: str):
        self.role_id = int(role_id)
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=emoji,
            custom_id=f"role_{role_id}",
        )

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        if not role:
            await interaction.response.send_message(
                f"❌ Role with ID {self.role_id} no longer exists.", ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            action = "removed from"

            # Log le changement
            interaction.client.log_to_file(
                "ROLE_REMOVE",
                f"User {interaction.user.name}#{interaction.user.discriminator} "
                f"(ID: {interaction.user.id}) removed role {role.name}",
            )
        else:
            await interaction.user.add_roles(role)
            action = "added to"

            # Log le changement
            interaction.client.log_to_file(
                "ROLE_ADD",
                f"User {interaction.user.name}#{interaction.user.discriminator} "
                f"(ID: {interaction.user.id}) received role {role.name}",
            )

        await interaction.response.send_message(
            f"✅ Role {role.mention} {action} you!", ephemeral=True
        )


class AutoroleSetupView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.update_buttons()

    def update_buttons(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "toggle":
                child.style = (
                    discord.ButtonStyle.green
                    if self.bot.config["autorole"]["enabled"]
                    else discord.ButtonStyle.red
                )
                child.label = f"Autorole: {'Enabled' if self.bot.config['autorole']['enabled'] else 'Disabled'}"

    @discord.ui.button(label="Set Channel", style=discord.ButtonStyle.primary)
    async def set_channel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        modal = AutoroleChannelModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Add Role", style=discord.ButtonStyle.primary)
    async def add_role(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        modal = AddRoleModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Remove Role", style=discord.ButtonStyle.primary)
    async def remove_role(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        modal = RemoveRoleModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Autorole: Disabled", style=discord.ButtonStyle.red, custom_id="toggle"
    )
    async def toggle_autorole(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.bot.config["autorole"]["enabled"] = not self.bot.config["autorole"][
            "enabled"
        ]
        self.bot.save_config()
        self.update_buttons()

        # Mettre à jour le message des rôles si nécessaire
        if self.bot.config["autorole"]["enabled"]:
            await self.update_role_message(interaction)

        await interaction.response.edit_message(view=self)

    async def update_role_message(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(
            self.bot.config["autorole"]["channel_id"]
        )
        if not channel:
            return

        try:
            view = RoleView(self.bot)

            if self.bot.config["autorole"]["message_id"]:
                try:
                    message = await channel.fetch_message(
                        self.bot.config["autorole"]["message_id"]
                    )
                    await message.edit(view=view)
                    self.bot.add_view(view, message_id=message.id)
                    return
                except discord.NotFound:
                    pass

            message = await channel.send("🎭 **Choisissez vos rôles**", view=view)
            self.bot.config["autorole"]["message_id"] = message.id
            self.bot.save_config()
            self.bot.add_view(view, message_id=message.id)

        except Exception as e:
            print(f"Erreur mise à jour message: {str(e)}")


class AutoroleChannelModal(discord.ui.Modal, title="Autorole Channel Setup"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    channel_id = discord.ui.TextInput(
        label="Channel ID",
        placeholder="Enter the channel ID for autoroles",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel_id.value)
            channel = interaction.guild.get_channel(channel_id)

            if not channel or not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message(
                    "❌ Invalid channel!", ephemeral=True
                )
                return

            self.bot.config["autorole"]["channel_id"] = channel_id
            self.bot.save_config()

            # Mettre à jour ou créer le message des rôles
            if self.bot.config["autorole"]["enabled"]:
                view = AutoroleSetupView(self.bot)
                await view.update_role_message(interaction)

            await interaction.response.send_message(
                f"✅ Autorole channel set to {channel.mention}!", ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)


class AddRoleModal(discord.ui.Modal, title="Add Autorole"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    role_id = discord.ui.TextInput(
        label="Role ID", placeholder="Enter the role ID", required=True
    )

    emoji = discord.ui.TextInput(
        label="Emoji",
        placeholder="Enter the emoji for this role",
        required=True,
        max_length=2,  # Pour les emojis Unicode standard
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            role_id = int(self.role_id.value)
            role = interaction.guild.get_role(role_id)

            if not role:
                await interaction.response.send_message(
                    f"❌ Invalid role! ID: {role_id} not found.", ephemeral=True
                )
                return

            self.bot.config["autorole"]["roles"][str(role_id)] = self.emoji.value
            self.bot.save_config()

            # Debug: afficher les rôles actuels
            print(f"Rôles actuels: {self.bot.config['autorole']['roles']}")

            # Mettre à jour le message des rôles
            if self.bot.config["autorole"]["enabled"]:
                view = AutoroleSetupView(self.bot)
                await view.update_role_message(interaction)

            await interaction.response.send_message(
                f"✅ Added {self.emoji.value} - {role.mention} to autoroles!",
                ephemeral=True,
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid role ID!", ephemeral=True
            )


class RemoveRoleModal(discord.ui.Modal, title="Remove Autorole"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    role_id = discord.ui.TextInput(
        label="Role ID", placeholder="Enter the role ID to remove", required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            role_id = str(int(self.role_id.value))

            if role_id not in self.bot.config["autorole"]["roles"]:
                await interaction.response.send_message(
                    "❌ This role is not in autoroles!", ephemeral=True
                )
                return

            del self.bot.config["autorole"]["roles"][role_id]
            self.bot.save_config()

            # Mettre à jour le message des rôles
            if self.bot.config["autorole"]["enabled"]:
                view = AutoroleSetupView(self.bot)
                await view.update_role_message(interaction)

            await interaction.response.send_message(
                "✅ Role removed from autoroles!", ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid role ID!", ephemeral=True
            )


class Autorole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.setup_views()

    def setup_views(self):
        """Réinitialise les vues persistantes au démarrage"""
        if self.bot.config["autorole"].get("message_id"):
            view = RoleView(self.bot)
            self.bot.add_view(
                view, message_id=self.bot.config["autorole"]["message_id"]
            )

    async def cog_load(self):
        """Restaure les messages après redémarrage"""
        if self.bot.config["autorole"]["enabled"]:
            for guild in self.bot.guilds:
                try:
                    channel_id = self.bot.config["autorole"]["channel_id"]
                    message_id = self.bot.config["autorole"]["message_id"]

                    if not channel_id or not message_id:
                        continue

                    channel = guild.get_channel(channel_id)
                    if channel:
                        message = await channel.fetch_message(message_id)
                        view = RoleView(self.bot)
                        await message.edit(view=view)

                except Exception as e:
                    print(f"Erreur restauration autorole: {str(e)}")


async def setup(bot):
    await bot.add_cog(Autorole(bot))
