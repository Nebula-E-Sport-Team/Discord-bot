import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Affiche la liste des commandes disponibles"
    )
    @app_commands.describe(
        category="Catégorie de commandes spécifique (optionnel)"
    )
    async def help(
        self, 
        interaction: discord.Interaction,
        category: Optional[str] = None
    ):
        categories = {
            "moderation": {
                "name": "🛡️ Modération",
                "commands": [
                    ("/purge [amount] [user] [contains]", "Supprimer des messages"),
                    ("/infractions [user]", "Voir l'historique des infractions"),
                    ("/add-banned-word [word]", "Ajouter un mot interdit"),
                    ("/remove-banned-word [word]", "Retirer un mot interdit"),
                    ("/list-banned-words", "Lister les mots interdits"),
                    ("/toggle-moderation", "Activer/désactiver la modération"),
                    ("/set-timeout-duration [minutes]", "Définir la durée des timeouts")
                ]
            },
            "voice": {
                "name": "🎤 Salons Vocaux",
                "commands": [
                    ("/voc-mute [user]", "Rendre muet dans votre salon"),
                    ("/voc-ban [user]", "Bannir de votre salon"),
                    ("/voc-rename [name]", "Renommer votre salon"),
                    ("/voc-limit [limit]", "Définir une limite d'utilisateurs"),
                    ("/voc-close", "Fermer votre salon"),
                    ("/voc-open", "Ouvrir votre salon")
                ]
            },
            "tickets": {
                "name": "🎫 Tickets",
                "commands": [
                    ("/setup tickets", "Configurer le système de tickets"),
                    ("Bouton 'Create Ticket'", "Créer un nouveau ticket"),
                    ("Bouton 'Close'", "Fermer un ticket"),
                    ("Bouton 'Delete'", "Supprimer un ticket fermé")
                ]
            },
            "reminders": {
                "name": "⏰ Rappels",
                "commands": [
                    ("/remind [time] [message]", "Créer un rappel"),
                    ("/list-reminders", "Voir vos rappels actifs"),
                    ("/cancel-reminder [id]", "Annuler un rappel")
                ]
            },
            "polls": {
                "name": "📊 Sondages",
                "commands": [
                    ("/poll [question] [duration] [options]", "Créer un sondage"),
                    ("/endpoll [message_id]", "Terminer un sondage manuellement")
                ]
            },
            "autorole": {
                "name": "🔄 Auto-Rôles",
                "commands": [
                    ("/setup autorole", "Configurer le système d'auto-rôles"),
                    ("Menu des rôles", "Obtenir/Retirer des rôles automatiquement")
                ]
            },
            "setup": {
                "name": "⚙️ Configuration",
                "commands": [
                    ("/setup", "Menu principal de configuration"),
                    ("Channel Settings", "Configuration des salons"),
                    ("Logs Settings", "Configuration des logs"),
                    ("Moderation Settings", "Configuration de la modération"),
                    ("Autorole Settings", "Configuration de l'auto-rôle")
                ]
            }
        }

        if category and category.lower() in categories:
            # Afficher une catégorie spécifique
            cat = categories[category.lower()]
            embed = discord.Embed(
                title=f"{cat['name']} - Commandes",
                color=discord.Color.blue()
            )
            
            for cmd, desc in cat["commands"]:
                embed.add_field(
                    name=cmd,
                    value=desc,
                    inline=False
                )
        
        else:
            # Afficher toutes les catégories
            embed = discord.Embed(
                title="📚 Aide - Commandes Disponibles",
                description="Utilisez `/help [catégorie]` pour plus de détails sur une catégorie",
                color=discord.Color.blue()
            )
            
            for cat_id, cat_data in categories.items():
                cmd_list = "\n".join(f"• {cmd[0]}" for cmd in cat_data["commands"][:3])
                if len(cat_data["commands"]) > 3:
                    cmd_list += "\n• ..."
                
                embed.add_field(
                    name=cat_data["name"],
                    value=f"```{cmd_list}```",
                    inline=False
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="logs",
        description="Affiche les logs du bot"
    )
    @app_commands.describe(
        type="Type de logs à afficher",
        lines="Nombre de lignes à afficher (défaut: 10)"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="🛡️ Modération", value="logs"),
        app_commands.Choice(name="💬 Messages", value="messages"),
        app_commands.Choice(name="⚙️ Changements", value="changes")
    ])
    @app_commands.default_permissions(administrator=True)
    async def logs(
        self,
        interaction: discord.Interaction,
        type: str,
        lines: Optional[int] = 10
    ):
        # Vérifier les permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Vous devez être administrateur pour voir les logs!",
                ephemeral=True
            )
            return

        # Mapper les types de logs aux fichiers
        log_files = {
            "logs": ("logs.txt", "🛡️ Logs de Modération"),
            "messages": ("messages.txt", "💬 Logs des Messages"),
            "changes": ("changes.txt", "⚙️ Logs des Changements")
        }

        if type not in log_files:
            await interaction.response.send_message(
                "❌ Type de logs invalide!",
                ephemeral=True
            )
            return

        filename, title = log_files[type]

        try:
            # Lire le fichier de logs
            with open(filename, "r", encoding="utf-8") as f:
                # Lire les dernières lignes
                all_lines = f.readlines()
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                if not last_lines:
                    await interaction.response.send_message(
                        "📝 Aucun log disponible pour le moment!",
                        ephemeral=True
                    )
                    return

                # Créer l'embed
                embed = discord.Embed(
                    title=f"📋 {title}",
                    description=f"Dernières {len(last_lines)} entrées:",
                    color=discord.Color.blue()
                )

                # Formater les logs
                log_content = "```\n"
                for line in last_lines:
                    # Limiter la longueur de chaque ligne pour l'affichage
                    if len(log_content) + len(line) > 1000:
                        log_content += "...\n"
                        break
                    log_content += line

                log_content += "```"
                
                embed.add_field(
                    name="Logs",
                    value=log_content,
                    inline=False
                )

                # Ajouter des informations supplémentaires
                embed.set_footer(
                    text=f"Total des logs: {len(all_lines)} | Affichage: {len(last_lines)}"
                )

                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True
                )

        except FileNotFoundError:
            await interaction.response.send_message(
                f"❌ Fichier de logs '{filename}' introuvable!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erreur lors de la lecture des logs: {str(e)}",
                ephemeral=True
            )

    async def cog_load(self):
        try:
            guild_id = int(os.getenv('GUILD_ID'))
            self.bot.tree.copy_global_to(guild=discord.Object(id=guild_id))
            await self.bot.tree.sync(guild=discord.Object(id=guild_id))
            print("Commandes help synchronisées")
        except Exception as e:
            print(f"Erreur sync help: {str(e)}")

async def setup(bot):
    await bot.add_cog(Help(bot)) 