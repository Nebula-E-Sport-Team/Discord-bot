import discord
from discord.ext import commands
import json
import os
from typing import Optional
from dotenv import load_dotenv
import datetime

# Chargement des variables d'environnement
load_dotenv()

class CustomBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        # Activation uniquement des intents nécessaires
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        super().__init__(
            command_prefix="!",  # Changé de None à "!" (ou n'importe quel préfixe)
            intents=intents,
            application_id=os.getenv('DISCORD_APP_ID'),
            help_command=None  # Désactive la commande help par défaut
        )
        
        self.config = self.load_config()
        
    async def setup_hook(self):
        print("Début de la configuration...")
        # Charger les cogs
        for cog in os.listdir("./cogs"):
            if cog.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{cog[:-3]}")
                    print(f"✓ {cog} chargé")
                except Exception as e:
                    print(f"✗ Erreur {cog}: {str(e)}")
        
        # Synchroniser les commandes
        try:
            synced = await self.tree.sync()
            print(f"Synchronisé {len(synced)} commandes")
        except Exception as e:
            print(f"Erreur synchronisation: {str(e)}")
        
    def load_config(self) -> dict:
        default_config = {
            "logs": {
                "voice": {
                    "enabled": False,
                    "events": {
                        "channel_create": False,
                        "channel_delete": False,
                        "channel_rename": False
                    }
                },
                "ticket": {
                    "enabled": False,
                    "events": {
                        "ticket_create": False,
                        "ticket_close": False,
                        "ticket_delete": False
                    }
                }
            },
            "jtc": {
                "category_id": None,
                "channel_id": None,
                "channel_name": "➕ Create Channel",
                "user_limit": 0,
                "created_channels": {}
            },
            "tickets": {
                "message_channel_id": None,
                "support_role_id": None,
                "category_id": None,
                "transcript_channel_id": None,
                "categories": {
                    "Technical": "🔧",
                    "Moderation": "🛡️",
                    "Other": "❓"
                },
                "active_tickets": {},
                "closed_tickets": {}
            },
            "moderation": {
                "enabled": True,
                "banned_words": [
                    "fuck", "shit", "bitch", "ass",
                    "putain", "merde", "connard", "salope", "pute"
                ],
                "timeout_duration": 30,  # en minutes
                "ban_duration": 7,      # en jours
                "mod_channel_id": None  # ID du salon pour les annonces de modération
            },
            "autorole": {
                "enabled": False,
                "channel_id": None,
                "message_id": None,
                "roles": {}  # {role_id: emoji}
            }
        }

        try:
            with open("config.json", "r") as f:
                try:
                    config = json.load(f)
                    # Ensure all required keys exist
                    if "logs" not in config:
                        config["logs"] = default_config["logs"]
                    if "voice" not in config["logs"]:
                        config["logs"]["voice"] = default_config["logs"]["voice"]
                    if "ticket" not in config["logs"]:
                        config["logs"]["ticket"] = default_config["logs"]["ticket"]
                    
                    # Vérifier les événements voice
                    if "events" not in config["logs"]["voice"]:
                        config["logs"]["voice"]["events"] = default_config["logs"]["voice"]["events"]
                    else:
                        for event in default_config["logs"]["voice"]["events"]:
                            if event not in config["logs"]["voice"]["events"]:
                                config["logs"]["voice"]["events"][event] = False
                    
                    # Vérifier les événements ticket
                    if "events" not in config["logs"]["ticket"]:
                        config["logs"]["ticket"]["events"] = default_config["logs"]["ticket"]["events"]
                    else:
                        for event in default_config["logs"]["ticket"]["events"]:
                            if event not in config["logs"]["ticket"]["events"]:
                                config["logs"]["ticket"]["events"][event] = False
                    
                    if "jtc" not in config:
                        config["jtc"] = default_config["jtc"]
                    
                    if "tickets" not in config:
                        config["tickets"] = default_config["tickets"]
                    
                    if "moderation" not in config:
                        config["moderation"] = default_config["moderation"]
                    else:
                        # S'assurer que toutes les sous-clés existent
                        if "enabled" not in config["moderation"]:
                            config["moderation"]["enabled"] = default_config["moderation"]["enabled"]
                        if "banned_words" not in config["moderation"]:
                            config["moderation"]["banned_words"] = default_config["moderation"]["banned_words"]
                    
                    if "autorole" not in config:
                        config["autorole"] = default_config["autorole"]
                    
                    with open("config.json", "w") as f2:
                        json.dump(config, f2, indent=4)
                    return config
                except json.JSONDecodeError:
                    with open("config.json", "w") as f2:
                        json.dump(default_config, f2, indent=4)
                    return default_config
        except FileNotFoundError:
            with open("config.json", "w") as f:
                json.dump(default_config, f, indent=4)
            return default_config

    def log_to_file(self, event_type: str, message: str):
        """Write a log message to the logs file"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{event_type}] {message}\n"
        
        with open("logs.txt", "a", encoding="utf-8") as f:
            f.write(log_entry)

    def save_config(self):
        with open("config.json", "w") as f:
            json.dump(self.config, f, indent=4)

bot = CustomBot()

@bot.event
async def on_ready():
    print("="*50)
    print(f"Bot connecté en tant que {bot.user}")
    print(f"ID du bot: {bot.user.id}")
    print("\nLien d'invitation du bot:")
    print(f"https://discord.com/api/oauth2/authorize?client_id={bot.application_id}&permissions=8&scope=bot%20applications.commands")
    print("="*50)

bot.run(os.getenv('DISCORD_TOKEN')) 