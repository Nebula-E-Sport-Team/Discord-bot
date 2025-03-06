import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import json
import asyncio
import re

class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminders = self.load_reminders()
        self.reminder_tasks = {}
        # Redémarrer les rappels existants
        asyncio.create_task(self.start_reminders())
    
    def load_reminders(self) -> dict:
        try:
            with open("reminders.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            reminders = {}
            self.save_reminders(reminders)
            return reminders
    
    def save_reminders(self, reminders: dict):
        with open("reminders.json", "w") as f:
            json.dump(reminders, f, indent=4)
    
    def parse_time(self, time_str: str) -> timedelta:
        """Convertit une chaîne de temps (ex: 1h30m) en timedelta"""
        total_seconds = 0
        pattern = re.compile(r'(\d+)([dhms])')
        
        for value, unit in pattern.findall(time_str.lower()):
            value = int(value)
            if unit == 'd':
                total_seconds += value * 86400
            elif unit == 'h':
                total_seconds += value * 3600
            elif unit == 'm':
                total_seconds += value * 60
            elif unit == 's':
                total_seconds += value
        
        if total_seconds == 0:
            raise ValueError("Invalid time format")
        
        return timedelta(seconds=total_seconds)
    
    async def start_reminders(self):
        """Redémarre tous les rappels au démarrage du bot"""
        for user_id, user_reminders in self.reminders.items():
            for reminder_id, reminder in user_reminders.items():
                if not reminder["completed"]:
                    time_left = datetime.fromisoformat(reminder["end_time"]) - datetime.now()
                    if time_left.total_seconds() > 0:
                        self.reminder_tasks[reminder_id] = asyncio.create_task(
                            self.send_reminder(user_id, reminder_id)
                        )
    
    async def send_reminder(self, user_id: str, reminder_id: str):
        """Envoie un rappel à l'utilisateur"""
        reminder = self.reminders[user_id][reminder_id]
        end_time = datetime.fromisoformat(reminder["end_time"])
        
        # Attendre jusqu'à l'heure du rappel
        await discord.utils.sleep_until(end_time)
        
        try:
            user = await self.bot.fetch_user(int(user_id))
            embed = discord.Embed(
                title="⏰ Reminder",
                description=reminder["message"],
                color=discord.Color.blue()
            )
            embed.add_field(name="Set at", value=reminder["created_at"])
            await user.send(embed=embed)
            
            # Marquer comme complété
            reminder["completed"] = True
            self.save_reminders(self.reminders)
            
        except discord.NotFound:
            pass  # Utilisateur introuvable
        except discord.Forbidden:
            pass  # DMs fermés
        
        # Nettoyer la tâche
        if reminder_id in self.reminder_tasks:
            del self.reminder_tasks[reminder_id]
    
    @app_commands.command(
        name="remind",
        description="Set a reminder"
    )
    @app_commands.describe(
        time="Time until reminder (format: 1d2h3m4s)",
        message="Message to remind you about"
    )
    async def remind(self, interaction: discord.Interaction, time: str, message: str):
        try:
            duration = self.parse_time(time)
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid time format! Use format like: 1d2h3m4s\n"
                "Examples: 1h30m, 24h, 30m",
                ephemeral=True
            )
            return
        
        user_id = str(interaction.user.id)
        if user_id not in self.reminders:
            self.reminders[user_id] = {}
        
        # Créer un nouveau rappel
        reminder_id = str(len(self.reminders[user_id]) + 1)
        now = datetime.now()
        end_time = now + duration
        
        reminder = {
            "message": message,
            "created_at": now.isoformat(),
            "end_time": end_time.isoformat(),
            "completed": False
        }
        
        self.reminders[user_id][reminder_id] = reminder
        self.save_reminders(self.reminders)
        
        # Démarrer la tâche de rappel
        self.reminder_tasks[reminder_id] = asyncio.create_task(
            self.send_reminder(user_id, reminder_id)
        )
        
        # Envoyer la confirmation
        await interaction.response.send_message(
            f"✅ I'll remind you about: {message}\n"
            f"⏰ Time: {time} (at {end_time.strftime('%Y-%m-%d %H:%M:%S')})",
            ephemeral=True
        )
    
    @app_commands.command(
        name="list-reminders",
        description="List all your active reminders"
    )
    async def list_reminders(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in self.reminders or not self.reminders[user_id]:
            await interaction.response.send_message("You have no reminders set", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Your Reminders",
            color=discord.Color.blue()
        )
        
        for reminder_id, reminder in self.reminders[user_id].items():
            if not reminder["completed"]:
                end_time = datetime.fromisoformat(reminder["end_time"])
                time_left = end_time - datetime.now()
                
                if time_left.total_seconds() > 0:
                    embed.add_field(
                        name=f"Reminder #{reminder_id}",
                        value=(
                            f"Message: {reminder['message']}\n"
                            f"Time left: {str(time_left).split('.')[0]}\n"
                            f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        ),
                        inline=False
                    )
        
        if not embed.fields:
            await interaction.response.send_message("You have no active reminders", ephemeral=True)
            return
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="cancel-reminder",
        description="Cancel a specific reminder"
    )
    @app_commands.describe(reminder_id="The ID of the reminder to cancel")
    async def cancel_reminder(self, interaction: discord.Interaction, reminder_id: str):
        user_id = str(interaction.user.id)
        
        if (user_id not in self.reminders or 
            reminder_id not in self.reminders[user_id] or 
            self.reminders[user_id][reminder_id]["completed"]):
            await interaction.response.send_message("❌ Reminder not found", ephemeral=True)
            return
        
        # Annuler la tâche
        if reminder_id in self.reminder_tasks:
            self.reminder_tasks[reminder_id].cancel()
            del self.reminder_tasks[reminder_id]
        
        # Marquer comme complété
        self.reminders[user_id][reminder_id]["completed"] = True
        self.save_reminders(self.reminders)
        
        await interaction.response.send_message("✅ Reminder cancelled", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Reminders(bot)) 