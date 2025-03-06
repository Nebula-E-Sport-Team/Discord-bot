import discord
from discord.ext import commands
from discord import app_commands


class ForumLinks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="lier", description="Lier un salon au forum avec des tags spécifiques"
    )
    @app_commands.describe(
        channel="Le salon à lier",
        tags="Les tags à appliquer (séparés par des virgules)",
    )
    @app_commands.default_permissions(administrator=True)
    async def link_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel, tags: str
    ):
        # Vérifier si un forum est configuré
        if not self.bot.config.get("forum", {}).get("channel_id"):
            await interaction.response.send_message(
                "❌ Aucun forum n'est configuré! Utilisez `/setup` d'abord.",
                ephemeral=True,
            )
            return

        # Récupérer le forum
        forum = interaction.guild.get_channel(self.bot.config["forum"]["channel_id"])
        if not forum or not isinstance(forum, discord.ForumChannel):
            await interaction.response.send_message(
                "❌ Forum introuvable ou invalide! Vérifiez la configuration.",
                ephemeral=True,
            )
            return

        # Vérifier si le forum a des tags disponibles
        if not forum.available_tags:
            await interaction.response.send_message(
                "❌ Le forum n'a pas de tags configurés! Ajoutez des tags au forum d'abord.",
                ephemeral=True,
            )
            return

        # Vérifier les tags
        tag_names = [tag.strip() for tag in tags.split(",")]
        valid_tags = []
        invalid_tags = []

        for tag_name in tag_names:
            tag = discord.utils.get(forum.available_tags, name=tag_name)
            if tag:
                valid_tags.append(tag.id)
            else:
                invalid_tags.append(tag_name)

        if invalid_tags:
            await interaction.response.send_message(
                f"❌ Tags invalides: {', '.join(invalid_tags)}\n"
                f"Tags disponibles: {', '.join(t.name for t in forum.available_tags)}",
                ephemeral=True,
            )
            return

        if not valid_tags:
            await interaction.response.send_message(
                "❌ Aucun tag valide spécifié!", ephemeral=True
            )
            return

        # Sauvegarder la liaison
        if "links" not in self.bot.config["forum"]:
            self.bot.config["forum"]["links"] = {}

        self.bot.config["forum"]["links"][str(channel.id)] = {"tags": valid_tags}
        self.bot.save_config()

        await interaction.response.send_message(
            f"✅ Salon {channel.mention} lié avec succès!\n"
            f"Tags: {', '.join(tag_names)}",
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            # Vérifier si c'est un message de serveur suivi
            if not message.flags.crossposted and not message.flags.is_crossposted:
                return

            # Vérifier si le salon est lié
            forum_config = self.bot.config.get("forum", {})
            channel_links = forum_config.get("links", {})

            if str(message.channel.id) not in channel_links:
                return

            # Récupérer le forum et les tags
            forum = message.guild.get_channel(forum_config["channel_id"])
            if not forum or not isinstance(forum, discord.ForumChannel):
                print(f"Forum invalide ou introuvable: {forum_config['channel_id']}")
                return

            link_config = channel_links[str(message.channel.id)]

            # Vérifier si le forum a des tags disponibles
            if not forum.available_tags:
                print(f"Le forum {forum.name} n'a pas de tags disponibles")
                return

            # Récupérer les tags valides
            tags = []
            for tag_id in link_config["tags"]:
                tag = discord.utils.get(forum.available_tags, id=tag_id)
                if tag:
                    tags.append(tag)

            if not tags:
                print(f"Aucun tag valide trouvé pour le salon {message.channel.name}")
                return

            # Créer le titre du post
            title = (
                message.content.split("\n")[0][:100]
                if message.content
                else "Nouveau message"
            )

            # Créer le contenu du post avec les informations du serveur d'origine
            content = []
            content.append(f"**Message du serveur {message.guild.name}**")
            content.append(f"**Canal:** #{message.channel.name}")
            if message.author:
                content.append(f"**Auteur:** {message.author.name}")

            # Ajouter le contenu du message
            if message.content:
                content.append("\n**Message:**")
                content.append(message.content)

            # Ajouter les embeds s'il y en a
            if message.embeds:
                for embed in message.embeds:
                    if embed.title:
                        content.append(f"\n**{embed.title}**")
                    if embed.description:
                        content.append(embed.description)
                    for field in embed.fields:
                        content.append(f"\n**{field.name}**")
                        content.append(field.value)

            final_content = "\n".join(content)

            # Créer le thread
            files = []
            for attachment in message.attachments:
                try:
                    files.append(await attachment.to_file())
                except discord.HTTPException:
                    content.append(
                        f"\n[Pièce jointe non téléchargeable: {attachment.url}]"
                    )

            try:
                # Créer le thread avec la bonne méthode
                thread, starter_message = await forum.create_thread(
                    name=title,
                    content=final_content,
                    applied_tags=tags,
                    files=files,  # Remplacer "files=files if files else None" par "files=files"
                    reason="Message automatique depuis un salon lié",
                )

                # Log la création
                self.bot.log_to_file(
                    "FORUM_LINK",
                    f"Message du serveur {message.guild.name} dans #{message.channel.name} "
                    f"transféré vers {thread.name}",
                )

            except discord.Forbidden:
                print("Erreur: Permissions insuffisantes pour créer un thread")
            except discord.HTTPException as e:
                print(f"Erreur HTTP lors de la création du thread: {e}")

        except Exception as e:
            print(f"Erreur lors de la création du thread: {str(e)}")
            print(f"Message: {message.content}")
            print(f"Salon: {message.channel.name}")
            if message.guild:
                print(f"Serveur: {message.guild.name}")
            # Debug plus détaillé
            print(f"Tags disponibles: {[(t.name, t.id) for t in forum.available_tags]}")
            print(f"Tags sélectionnés: {[(t.name, t.id) for t in tags]}")
            print(f"Type de tags: {type(tags)}")
            print(f"Type de premier tag: {type(tags[0]) if tags else 'Pas de tag'}")


async def setup(bot):
    await bot.add_cog(ForumLinks(bot))
