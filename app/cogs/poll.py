import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import re
import io
import matplotlib.pyplot as plt


class PollView(discord.ui.View):
    def __init__(self, options, duration, multiple_choice=False):
        super().__init__(timeout=None)
        self.options = options
        self.votes = {option: [] for option in options}
        self.end_time = datetime.now() + duration
        self.ended = False
        self.multiple_choice = multiple_choice

        for i, option in enumerate(options):
            button = discord.ui.Button(
                label=f"{option} (0)",
                custom_id=f"poll_{i}",
                style=discord.ButtonStyle.primary,
                row=i // 4,
            )
            button.callback = self.make_callback(option)
            self.add_item(button)

    def make_callback(self, option):
        async def callback(interaction: discord.Interaction):
            if self.ended:
                await interaction.response.send_message(
                    "Ce sondage est terminé!", ephemeral=True
                )
                return

            user_id = interaction.user.id

            if not self.multiple_choice:
                for opt in self.votes:
                    if user_id in self.votes[opt]:
                        self.votes[opt].remove(user_id)

            if user_id in self.votes[option]:
                self.votes[option].remove(user_id)
                action = "retiré de"
            else:
                self.votes[option].append(user_id)
                action = "ajouté à"

            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    opt = self.options[int(child.custom_id.split("_")[1])]
                    child.label = f"{opt} ({len(self.votes[opt])})"

            await interaction.response.edit_message(view=self)
            await interaction.followup.send(
                f"Vote {action} l'option '{option}'!", ephemeral=True
            )

        return callback

    def get_results(self):
        results = {opt: len(votes) for opt, votes in self.votes.items()}
        total_votes = sum(results.values())
        if total_votes == 0:
            return results, {opt: 0 for opt in self.options}

        percentages = {
            opt: (votes / total_votes) * 100 for opt, votes in results.items()
        }
        return results, percentages


class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_polls = {}

    def parse_time(self, time_str: str) -> timedelta:
        total_seconds = 0
        pattern = re.compile(r"(\d+)([dhms])")

        for value, unit in pattern.findall(time_str.lower()):
            value = int(value)
            if unit == "d":
                total_seconds += value * 86400
            elif unit == "h":
                total_seconds += value * 3600
            elif unit == "m":
                total_seconds += value * 60
            elif unit == "s":
                total_seconds += value

        if total_seconds == 0:
            raise ValueError("Invalid time format")

        return timedelta(seconds=total_seconds)

    async def create_results_image(
        self, question: str, results: dict, percentages: dict
    ):
        plt.figure(figsize=(10, 6))

        options = list(results.keys())
        votes = list(results.values())

        bars = plt.bar(options, votes)

        plt.title(question)
        plt.ylabel("Votes")

        for i, bar in enumerate(bars):
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{percentages[options[i]]:.1f}%",
                ha="center",
                va="bottom",
            )

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        plt.close()

        return discord.File(buf, "poll_results.png")

    @app_commands.command(name="poll", description="Créer un sondage")
    @app_commands.describe(
        question="La question du sondage",
        duration="Durée du sondage (ex: 1h30m)",
        options="Options séparées par des virgules",
        multiple_choice="Autoriser les votes multiples",
    )
    async def create_poll(
        self,
        interaction: discord.Interaction,
        question: str,
        duration: str,
        options: str,
        multiple_choice: bool = False,
    ):
        try:
            poll_duration = self.parse_time(duration)

            poll_options = [opt.strip() for opt in options.split(",")]
            if len(poll_options) < 2:
                await interaction.response.send_message(
                    "❌ Vous devez spécifier au moins 2 options!", ephemeral=True
                )
                return

            view = PollView(poll_options, poll_duration, multiple_choice)

            embed = discord.Embed(
                title=question,
                description="Cliquez sur un bouton pour voter!",
                color=discord.Color.blue(),
            )
            embed.add_field(
                name="Type de vote",
                value="Choix multiples autorisés"
                if multiple_choice
                else "Un seul choix possible",
                inline=True,
            )
            embed.add_field(
                name="Durée",
                value=f"Se termine le {view.end_time.strftime('%Y-%m-%d %H:%M:%S')}",
            )

            await interaction.response.send_message(embed=embed, view=view)
            message = await interaction.original_response()

            self.active_polls[message.id] = view

            self.bot.loop.create_task(self.end_poll(message, view, question))

        except ValueError as e:
            await interaction.response.send_message(
                f"❌ Erreur: {str(e)}", ephemeral=True
            )

    @app_commands.command(
        name="endpoll", description="Terminer un sondage manuellement"
    )
    @app_commands.describe(message_id="ID du message du sondage")
    async def end_poll_command(self, interaction: discord.Interaction, message_id: str):
        try:
            await interaction.response.defer(ephemeral=True)

            message_id = int(message_id)
            if message_id not in self.active_polls:
                await interaction.followup.send(
                    "❌ Sondage non trouvé!", ephemeral=True
                )
                return

            view = self.active_polls[message_id]
            if view.ended:
                await interaction.followup.send(
                    "❌ Ce sondage est déjà terminé!", ephemeral=True
                )
                return

            try:
                message = await interaction.channel.fetch_message(message_id)
            except discord.NotFound:
                await interaction.followup.send(
                    "❌ Message du sondage introuvable dans ce canal!", ephemeral=True
                )
                del self.active_polls[message_id]
                return

            # Forcer la fin du sondage immédiatement
            view.end_time = datetime.now()
            await self.end_poll(message, view, message.embeds[0].title)
            await interaction.followup.send(
                "✅ Sondage terminé avec succès!", ephemeral=True
            )

        except ValueError:
            await interaction.followup.send(
                "❌ Format d'ID invalide! Utilisez un nombre entier.", ephemeral=True
            )

    async def end_poll(self, message: discord.Message, view: PollView, question: str):
        if view.ended:
            return

        if datetime.now() < view.end_time:
            await discord.utils.sleep_until(view.end_time)

        # Marquer le sondage comme terminé
        view.ended = True

        # Désactiver tous les boutons
        for child in view.children:
            child.disabled = True

        await message.edit(view=view)

        results, percentages = view.get_results()

        results_file = await self.create_results_image(question, results, percentages)

        embed = discord.Embed(
            title=f"📊 Résultats: {question}", color=discord.Color.green()
        )

        if results:
            winner = max(results.items(), key=lambda x: x[1])
            embed.add_field(
                name="🏆 Gagnant",
                value=f"{winner[0]} avec {winner[1]} votes ({percentages[winner[0]]:.1f}%)",
                inline=False,
            )

        await message.reply(embed=embed, file=results_file)

        # Nettoyer le sondage des actifs
        if message.id in self.active_polls:
            del self.active_polls[message.id]

    async def cog_load(self):
        try:
            self.bot.tree.copy_global_to(guild=discord.Object(id=1338850831956447324))
            await self.bot.tree.sync(guild=discord.Object(id=1338850831956447324))
            print("Commandes poll synchronisées")
        except Exception as e:
            print(f"Erreur sync poll: {str(e)}")


async def setup(bot):
    await bot.add_cog(Poll(bot))
