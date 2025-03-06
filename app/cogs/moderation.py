import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import json
import re
import asyncio
from typing import Optional

MESSAGES_PATH = "/home/app/messages.txt"
INFRACTIONS_PATH = "/home/app/infractions.json"


class BannedWordsView(discord.ui.View):
    def __init__(self, bot, chunks):
        super().__init__(timeout=180)
        self.bot = bot
        self.chunks = chunks
        self.current_page = 0
        self.update_buttons()

    def update_buttons(self):
        self.previous_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= len(self.chunks) - 1

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.primary)
    async def previous_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await self.update_message(interaction)

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.primary)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current_page = min(len(self.chunks) - 1, self.current_page + 1)
        self.update_buttons()
        await self.update_message(interaction)

    async def update_message(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Banned Words List",
            description=f"Page {self.current_page + 1}/{len(self.chunks)}",
            color=discord.Color.red(),
        )

        chunk = self.chunks[self.current_page]
        embed.add_field(name="Words", value="\n".join(chunk), inline=False)

        await interaction.response.edit_message(embed=embed, view=self)


class ModActionView(discord.ui.View):
    def __init__(self, bot, user: discord.Member, action_type: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.user = user
        self.action_type = action_type
        self.result = None

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = False
        self.stop()
        await interaction.response.defer()


class ModerationSetupView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.update_buttons()

    def update_buttons(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "toggle":
                child.style = (
                    discord.ButtonStyle.green
                    if self.bot.config["moderation"]["enabled"]
                    else discord.ButtonStyle.red
                )
                child.label = f"Moderation: {'Enabled' if self.bot.config['moderation']['enabled'] else 'Disabled'}"

    @discord.ui.button(label="Set Mod Channel", style=discord.ButtonStyle.primary)
    async def set_channel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        modal = ModChannelModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Set Timeout Duration", style=discord.ButtonStyle.primary)
    async def set_timeout(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        modal = TimeoutDurationModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Set Ban Duration", style=discord.ButtonStyle.primary)
    async def set_ban(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        modal = BanDurationModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Moderation: Enabled", style=discord.ButtonStyle.green, custom_id="toggle"
    )
    async def toggle_moderation(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.bot.config["moderation"]["enabled"] = not self.bot.config["moderation"][
            "enabled"
        ]
        self.bot.save_config()
        self.update_buttons()
        await interaction.response.edit_message(view=self)


class ModChannelModal(discord.ui.Modal, title="Moderation Channel Setup"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    channel_id = discord.ui.TextInput(
        label="Channel ID", placeholder="Enter the moderation channel ID", required=True
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

            self.bot.config["moderation"]["mod_channel_id"] = channel_id
            self.bot.save_config()
            await interaction.response.send_message(
                f"✅ Moderation channel set to {channel.mention}!", ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)


class TimeoutDurationModal(discord.ui.Modal, title="Timeout Duration Setup"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    minutes = discord.ui.TextInput(
        label="Duration (minutes)",
        placeholder="Enter the timeout duration in minutes",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            minutes = int(self.minutes.value)
            if minutes < 1:
                await interaction.response.send_message(
                    "❌ Duration must be at least 1 minute!", ephemeral=True
                )
                return

            self.bot.config["moderation"]["timeout_duration"] = minutes
            self.bot.save_config()
            await interaction.response.send_message(
                f"✅ Timeout duration set to {minutes} minutes!", ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid duration!", ephemeral=True
            )


class BanDurationModal(discord.ui.Modal, title="Ban Duration Setup"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    days = discord.ui.TextInput(
        label="Duration (days)",
        placeholder="Enter the ban duration in days",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            days = int(self.days.value)
            if days < 1:
                await interaction.response.send_message(
                    "❌ Duration must be at least 1 day!", ephemeral=True
                )
                return

            self.bot.config["moderation"]["ban_duration"] = days
            self.bot.save_config()
            await interaction.response.send_message(
                f"✅ Ban duration set to {days} days!", ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid duration!", ephemeral=True
            )


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.infractions = self.load_infractions()

    def load_infractions(self) -> dict:
        """Charge les infractions depuis le fichier infractions.json"""
        try:
            with open(INFRACTIONS_PATH, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Si le fichier n'existe pas ou est corrompu, créer un nouveau
            infractions = {}
            self.save_infractions(infractions)
            return infractions

    def save_infractions(self, infractions: dict):
        """Sauvegarde les infractions dans le fichier infractions.json"""
        with open(INFRACTIONS_PATH, "w") as f:
            json.dump(infractions, f, indent=4)

    def get_user_data(self, user_id: str) -> dict:
        """Obtient ou crée les données d'un utilisateur"""
        if user_id not in self.infractions:
            self.infractions[user_id] = {
                "current_infractions": 0,
                "total_infractions": 0,
                "current_timeouts": 0,
                "total_timeouts": 0,
                "current_kicks": 0,
                "total_kicks": 0,
                "history": [],
            }
        return self.infractions[user_id]

    def check_message(self, content: str) -> str | None:
        """Vérifie si le message contient des mots interdits"""
        # Convertir le message en minuscules
        content = content.lower()

        # Séparer le message en mots (en gardant la ponctuation pour vérification)
        words = re.findall(r"\b\w+\b", content)

        for banned_word in self.bot.config["moderation"]["banned_words"]:
            # Vérifier si le mot banni est dans la liste des mots du message
            if banned_word in words:
                return banned_word

            # Vérifier aussi les combinaisons de mots (pour les phrases bannies)
            if " " in banned_word and banned_word in content:
                return banned_word

        return None

    def save_message(self, message: discord.Message):
        """Sauvegarde un message dans messages.txt"""
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        channel_name = (
            message.channel.name
            if isinstance(message.channel, (discord.TextChannel, discord.Thread))
            else "DM"
        )

        # Format: [timestamp] [server_name] [channel_name] author_name#discriminator (ID): message
        log_entry = (
            f"[{timestamp}] "
            f"[{message.guild.name}] "
            f"[#{channel_name}] "
            f"{message.author.name}#{message.author.discriminator} "
            f"(ID: {message.author.id}): "
            f"{message.content}"
        )

        # Ajouter les pièces jointes s'il y en a
        if message.attachments:
            attachments = [
                f"\n- Attachment: {attachment.url}"
                for attachment in message.attachments
            ]
            log_entry += "".join(attachments)

        # Ajouter les embeds s'il y en a
        if message.embeds:
            embeds = [
                f"\n- Embed: {embed.title} - {embed.description}"
                for embed in message.embeds
            ]
            log_entry += "".join(embeds)

        log_entry += "\n"

        with open(MESSAGES_PATH, "a", encoding="utf-8") as f:
            f.write(log_entry)

    async def handle_moderation(self, message: discord.Message, banned_word: str):
        user_id = str(message.author.id)
        user_data = self.get_user_data(user_id)

        # Ajouter l'infraction à l'historique
        infraction = {
            "type": "infraction",
            "word": banned_word,
            "message": message.content,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "channel_id": message.channel.id,
            "message_id": message.id,
        }
        user_data["history"].append(infraction)
        user_data["current_infractions"] += 1
        user_data["total_infractions"] += 1

        # Vérifier les conditions pour les actions de modération
        if user_data["current_kicks"] > 0:
            # Demande de ban après un kick
            await self.request_moderation_action(message.author, "ban")
        elif user_data["current_timeouts"] >= 3:
            # Demande de kick après 3 timeouts
            await self.request_moderation_action(message.author, "kick")
        elif user_data["current_infractions"] >= 5:
            # Demande de timeout après 5 infractions
            await self.request_moderation_action(message.author, "timeout")

        self.save_infractions(self.infractions)

    async def request_moderation_action(self, user: discord.Member, action_type: str):
        # Utiliser le salon configuré ou chercher mod-logs comme fallback
        mod_channel_id = self.bot.config["moderation"]["mod_channel_id"]
        mod_channel = None

        if mod_channel_id:
            mod_channel = user.guild.get_channel(mod_channel_id)

        if not mod_channel:
            mod_channel = discord.utils.get(user.guild.text_channels, name="mod-logs")
            if not mod_channel:
                return

        action_descriptions = {
            "timeout": f"User has {self.infractions[str(user.id)]['current_infractions']} infractions",
            "kick": f"User has {self.infractions[str(user.id)]['current_timeouts']} timeouts",
            "ban": "User received an infraction after being kicked",
        }

        embed = discord.Embed(
            title=f"Moderation Action Required: {action_type.upper()}",
            description=f"Action requested for {user.mention}\n"
            f"Reason: {action_descriptions[action_type]}",
            color=discord.Color.red(),
        )

        view = ModActionView(self.bot, user, action_type)
        msg = await mod_channel.send(embed=embed, view=view)

        # Attendre la réponse des modérateurs
        await view.wait()

        if view.result is True:
            user_data = self.get_user_data(str(user.id))

            if action_type == "timeout":
                duration = timedelta(
                    minutes=self.bot.config["moderation"]["timeout_duration"]
                )
                await user.timeout(duration)
                user_data["current_infractions"] = 0
                user_data["current_timeouts"] += 1
                user_data["total_timeouts"] += 1
            elif action_type == "kick":
                await user.kick(reason="Accumulated timeouts")
                user_data["current_timeouts"] = 0
                user_data["current_kicks"] += 1
                user_data["total_kicks"] += 1
            elif action_type == "ban":
                duration = timedelta(days=self.bot.config["moderation"]["ban_duration"])
                await user.ban(reason="Infraction after kick", delete_message_days=1)
                if self.bot.config["moderation"]["ban_duration"] > 0:
                    await asyncio.sleep(duration.total_seconds())
                    try:
                        await user.guild.unban(user, reason="Ban duration expired")
                    except discord.NotFound:
                        pass

            action_result = "accepted and executed"
        else:
            action_result = "rejected"

        # Mettre à jour le message
        embed.add_field(name="Result", value=f"Action {action_result}")
        await msg.edit(embed=embed, view=None)

        self.save_infractions(self.infractions)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignorer les messages des bots
        if message.author.bot:
            return

        # Sauvegarder le message
        if message.guild:  # Ne sauvegarder que les messages de serveur, pas les DMs
            self.save_message(message)

        # Continuer avec la vérification des mots interdits
        if not self.bot.config["moderation"]["enabled"]:
            return

        if banned_word := self.check_message(message.content):
            await self.handle_moderation(message, banned_word)

            # Notifier l'utilisateur
            try:
                embed = discord.Embed(
                    title="⚠️ Warning - Inappropriate Language",
                    description="Your message contained inappropriate language and has been logged.",
                    color=discord.Color.red(),
                )
                embed.add_field(
                    name="Message", value=f"```{message.content}```", inline=False
                )
                embed.add_field(
                    name="Banned Word", value=f"||{banned_word}||", inline=False
                )

                await message.author.send(embed=embed)
            except discord.Forbidden:
                pass  # L'utilisateur a peut-être bloqué les DMs

            # Log l'infraction
            self.bot.log_to_file(
                "MODERATION_INFRACTION",
                f"User: {message.author.name}#{message.author.discriminator} (ID: {message.author.id}) "
                f"used banned word '{banned_word}' in message: {message.content}",
            )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        # Ignorer les messages des bots
        if after.author.bot:
            return

        # Ne traiter que si le contenu a changé
        if before.content != after.content and after.guild:
            timestamp = after.edited_at.strftime("%Y-%m-%d %H:%M:%S")
            log_entry = (
                f"[{timestamp}] [EDIT] "
                f"[{after.guild.name}] "
                f"[#{after.channel.name}] "
                f"{after.author.name}#{after.author.discriminator} "
                f"(ID: {after.author.id})\n"
                f"Before: {before.content}\n"
                f"After: {after.content}\n"
            )

            with open(MESSAGES_PATH, "a", encoding="utf-8") as f:
                f.write(log_entry)

            # Vérifier les mots interdits dans le message édité
            if self.bot.config["moderation"]["enabled"]:
                if banned_word := self.check_message(after.content):
                    await self.handle_moderation(after, banned_word)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        # Ignorer les messages des bots
        if message.author.bot:
            return

        if message.guild:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = (
                f"[{timestamp}] [DELETE] "
                f"[{message.guild.name}] "
                f"[#{message.channel.name}] "
                f"{message.author.name}#{message.author.discriminator} "
                f"(ID: {message.author.id}): "
                f"{message.content}\n"
            )

            with open(MESSAGES_PATH, "a", encoding="utf-8") as f:
                f.write(log_entry)

    @app_commands.command(name="infractions", description="View infractions for a user")
    @app_commands.default_permissions(manage_messages=True)
    async def view_infractions(
        self, interaction: discord.Interaction, user: discord.Member
    ):
        user_id = str(user.id)
        if user_id not in self.infractions:
            await interaction.response.send_message(
                f"No infractions found for {user.mention}", ephemeral=True
            )
            return

        user_data = self.infractions[user_id]

        embed = discord.Embed(
            title=f"Moderation History for {user.name}#{user.discriminator}",
            color=discord.Color.red(),
        )

        # Statistiques générales
        stats = (
            f"Current Infractions: {user_data['current_infractions']}\n"
            f"Total Infractions: {user_data['total_infractions']}\n"
            f"Current Timeouts: {user_data['current_timeouts']}\n"
            f"Total Timeouts: {user_data['total_timeouts']}\n"
            f"Current Kicks: {user_data['current_kicks']}\n"
            f"Total Kicks: {user_data['total_kicks']}"
        )
        embed.add_field(name="Statistics", value=stats, inline=False)

        # Historique détaillé
        if user_data["history"]:
            history = []
            for entry in user_data["history"]:
                if entry["type"] == "infraction":
                    history.append(
                        f"[{entry['date']}] INFRACTION\n"
                        f"Word: {entry['word']}\n"
                        f"Message: {entry['message']}\n"
                    )
                elif entry["type"] == "timeout":
                    history.append(
                        f"[{entry['date']}] TIMEOUT\n"
                        f"Duration: {entry['duration']} minutes\n"
                        f"Reason: {entry.get('reason', 'No reason provided')}\n"
                    )
                elif entry["type"] == "kick":
                    history.append(
                        f"[{entry['date']}] KICK\n"
                        f"Reason: {entry.get('reason', 'No reason provided')}\n"
                    )
                elif entry["type"] == "ban":
                    history.append(
                        f"[{entry['date']}] BAN\n"
                        f"Duration: {entry.get('duration', 'Permanent')} days\n"
                        f"Reason: {entry.get('reason', 'No reason provided')}\n"
                    )

            # Diviser l'historique en champs de 1024 caractères max
            current_field = ""
            field_count = 1
            for entry in history:
                if len(current_field) + len(entry) > 1024:
                    embed.add_field(
                        name=f"History (Part {field_count})",
                        value=current_field,
                        inline=False,
                    )
                    current_field = entry
                    field_count += 1
                else:
                    current_field += entry + "\n"

            if current_field:
                embed.add_field(
                    name=f"History (Part {field_count})",
                    value=current_field,
                    inline=False,
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="clear-infractions",
        description="Clear all infractions and moderation history for a user",
    )
    @app_commands.default_permissions(administrator=True)
    async def clear_infractions(
        self, interaction: discord.Interaction, user: discord.Member
    ):
        user_id = str(user.id)
        if user_id not in self.infractions:
            await interaction.response.send_message(
                f"No infractions found for {user.mention}", ephemeral=True
            )
            return

        # Sauvegarder les anciennes données dans l'historique
        old_data = self.infractions[user_id]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Réinitialiser les données de l'utilisateur
        self.infractions[user_id] = {
            "current_infractions": 0,
            "total_infractions": old_data[
                "total_infractions"
            ],  # Garder le total historique
            "current_timeouts": 0,
            "total_timeouts": old_data["total_timeouts"],  # Garder le total historique
            "current_kicks": 0,
            "total_kicks": old_data["total_kicks"],  # Garder le total historique
            "history": old_data["history"],  # Garder l'historique
        }

        # Ajouter l'action de clear à l'historique
        self.infractions[user_id]["history"].append(
            {
                "type": "clear",
                "date": timestamp,
                "cleared_by": f"{interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id})",
            }
        )

        self.save_infractions(self.infractions)

        # Log l'action
        self.bot.log_to_file(
            "MODERATION",
            f"All current infractions cleared for {user.name}#{user.discriminator} "
            f"(ID: {user.id}) by {interaction.user.name}#{interaction.user.discriminator}",
        )

        await interaction.response.send_message(
            f"✅ All current infractions cleared for {user.mention}\n"
            f"Note: Historical totals and history entries are preserved",
            ephemeral=True,
        )

    @app_commands.command(
        name="add-banned-word",
        description="Add words to the banned words list (separate multiple words with commas)",
    )
    @app_commands.default_permissions(administrator=True)
    async def add_banned_word(self, interaction: discord.Interaction, words: str):
        # Séparer les mots par virgule et nettoyer les espaces
        word_list = [word.strip().lower() for word in words.split(",")]

        added_words = []
        already_exists = []

        for word in word_list:
            if not word:  # Ignorer les entrées vides
                continue

            if word in self.bot.config["moderation"]["banned_words"]:
                already_exists.append(word)
            else:
                self.bot.config["moderation"]["banned_words"].append(word)
                added_words.append(word)

        if added_words:
            self.bot.save_config()
            # Log l'ajout
            self.bot.log_to_file(
                "MODERATION_CONFIG",
                f"Banned words added by {interaction.user.name}#{interaction.user.discriminator} "
                f"(ID: {interaction.user.id}): {', '.join(added_words)}",
            )

        # Préparer le message de réponse
        response = []
        if added_words:
            response.append(
                f"✅ Added {len(added_words)} word(s): `{', '.join(added_words)}`"
            )
        if already_exists:
            response.append(
                f"ℹ️ {len(already_exists)} word(s) already banned: `{', '.join(already_exists)}`"
            )

        await interaction.response.send_message(
            "\n".join(response) or "No valid words provided", ephemeral=True
        )

    @app_commands.command(
        name="remove-banned-word",
        description="Remove a word from the banned words list",
    )
    @app_commands.default_permissions(administrator=True)
    async def remove_banned_word(self, interaction: discord.Interaction, word: str):
        # Convertir en minuscules pour la cohérence
        word = word.lower()

        if word not in self.bot.config["moderation"]["banned_words"]:
            await interaction.response.send_message(
                f"❌ The word `||{word}||` is not in the banned words list",
                ephemeral=True,
            )
            return

        self.bot.config["moderation"]["banned_words"].remove(word)
        self.bot.save_config()

        # Log la suppression
        self.bot.log_to_file(
            "MODERATION_CONFIG",
            f"Banned word removed by {interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id}): {word}",
        )

        await interaction.response.send_message(
            f"✅ Removed `||{word}||` from the banned words list", ephemeral=True
        )

    @app_commands.command(name="list-banned-words", description="View all banned words")
    @app_commands.default_permissions(manage_messages=True)
    async def list_banned_words(self, interaction: discord.Interaction):
        if not self.bot.config["moderation"]["banned_words"]:
            await interaction.response.send_message(
                "No words are currently banned", ephemeral=True
            )
            return

        # Grouper les mots par 20 pour chaque page
        words = sorted(
            self.bot.config["moderation"]["banned_words"]
        )  # Trier alphabétiquement
        chunks = [words[i : i + 20] for i in range(0, len(words), 20)]

        embed = discord.Embed(
            title="Banned Words List",
            description=f"Page 1/{len(chunks)}",
            color=discord.Color.red(),
        )

        embed.add_field(name="Words", value="\n".join(chunks[0]), inline=False)

        view = BannedWordsView(self.bot, chunks)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(
        name="toggle-moderation", description="Enable or disable word moderation"
    )
    @app_commands.default_permissions(administrator=True)
    async def toggle_moderation(self, interaction: discord.Interaction):
        self.bot.config["moderation"]["enabled"] = not self.bot.config["moderation"][
            "enabled"
        ]
        status = "enabled" if self.bot.config["moderation"]["enabled"] else "disabled"

        self.bot.save_config()

        # Log le changement
        self.bot.log_to_file(
            "MODERATION_CONFIG",
            f"Word moderation {status} by {interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id})",
        )

        await interaction.response.send_message(
            f"✅ Word moderation is now {status}", ephemeral=True
        )

    @app_commands.command(
        name="set-timeout-duration",
        description="Set the default timeout duration (in minutes)",
    )
    @app_commands.default_permissions(administrator=True)
    async def set_timeout_duration(
        self, interaction: discord.Interaction, minutes: int
    ):
        if minutes < 1:
            await interaction.response.send_message(
                "❌ Duration must be at least 1 minute", ephemeral=True
            )
            return

        self.bot.config["moderation"]["timeout_duration"] = minutes
        self.bot.save_config()

        self.bot.log_to_file(
            "MODERATION_CONFIG",
            f"Timeout duration set to {minutes} minutes by {interaction.user.name}#{interaction.user.discriminator}",
        )

        await interaction.response.send_message(
            f"✅ Default timeout duration set to {minutes} minutes", ephemeral=True
        )

    @app_commands.command(
        name="set-ban-duration", description="Set the default ban duration (in days)"
    )
    @app_commands.default_permissions(administrator=True)
    async def set_ban_duration(self, interaction: discord.Interaction, days: int):
        if days < 1:
            await interaction.response.send_message(
                "❌ Duration must be at least 1 day", ephemeral=True
            )
            return

        self.bot.config["moderation"]["ban_duration"] = days
        self.bot.save_config()

        self.bot.log_to_file(
            "MODERATION_CONFIG",
            f"Ban duration set to {days} days by {interaction.user.name}#{interaction.user.discriminator}",
        )

        await interaction.response.send_message(
            f"✅ Default ban duration set to {days} days", ephemeral=True
        )

    @app_commands.command(
        name="set-mod-channel",
        description="Set the channel for moderation announcements",
    )
    @app_commands.default_permissions(administrator=True)
    async def set_mod_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        self.bot.config["moderation"]["mod_channel_id"] = channel.id
        self.bot.save_config()

        self.bot.log_to_file(
            "MODERATION_CONFIG",
            f"Moderation channel set to #{channel.name} by {interaction.user.name}#{interaction.user.discriminator}",
        )

        await interaction.response.send_message(
            f"✅ Moderation channel set to {channel.mention}", ephemeral=True
        )

    @app_commands.command(
        name="purge",
        description="Delete a specified number of messages from the channel",
    )
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        user="Only delete messages from this user (optional)",
        contains="Only delete messages containing this text (optional)",
    )
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
        user: Optional[discord.Member] = None,
        contains: Optional[str] = None,
    ):
        # Vérifier les permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ You need the 'Manage Messages' permission to use this command",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        def check_message(message):
            # Vérifier l'auteur si spécifié
            if user and message.author.id != user.id:
                return False

            # Vérifier le contenu si spécifié
            if contains and contains.lower() not in message.content.lower():
                return False

            return True

        try:
            # Supprimer le message de commande
            await interaction.channel.purge(
                limit=amount, check=check_message, before=interaction.created_at
            )

            # Préparer le message de confirmation
            details = []
            if user:
                details.append(f"from {user.mention}")
            if contains:
                details.append(f"containing '{contains}'")

            details_text = " ".join(details)
            if details_text:
                details_text = f" {details_text}"

            # Log l'action
            self.bot.log_to_file(
                "MODERATION",
                f"{interaction.user.name}#{interaction.user.discriminator} "
                f"purged {amount} messages{details_text} in #{interaction.channel.name}",
            )

            await interaction.followup.send(
                f"✅ Successfully deleted {amount} messages{details_text}",
                ephemeral=True,
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to delete messages in this channel",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ An error occurred while deleting messages: {str(e)}",
                ephemeral=True,
            )

    @commands.command(name="reload-mod")
    @commands.is_owner()
    async def reload_mod(self, ctx):
        """Recharge le cog de modération et synchronise les commandes"""
        try:
            await self.bot.reload_extension("cogs.moderation")
            await self.bot.tree.sync()
            await ctx.send("✅ Cog de modération rechargé et commandes synchronisées")
        except Exception as e:
            await ctx.send(f"❌ Erreur: {str(e)}")

    async def cog_load(self):
        """Appelé quand le cog est chargé"""
        try:
            await self.bot.tree.sync()
            print("✓ Commandes de modération synchronisées")
        except Exception as e:
            print(
                f"✗ Erreur lors de la synchronisation des commandes de modération: {str(e)}"
            )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
