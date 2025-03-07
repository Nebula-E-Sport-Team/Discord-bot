# Discord-bot

> A complete discord bot to manage the Nebula Team discord server.

## Features

- [x] Welcome message
- [ ] ...

## Installation

First, clone the repository:

```bash
git clone https://github.com/Nebula-E-Sport-Team/Discord-bot.git
cd Discord-bot
```

Then we update the environment variables:

- `DISCORD_TOKEN`: a unique token, a string of letters and numbers, that is used to log in to the bot account, found in the developer portal
- `DISCORD_APP_ID`: similar to the token, but it is a number, and it is used to invite the bot to the server, also found in the developer portal
- `DISCORD_GUILD_ID`: similar to the app id, but it is the id of the server, found in the settings of the server on the app after activating the developer mode on discord.

We can create a `.env` file in the root of the project with the following content:

````bash
cp .env.example .env
````

Then we update the values of the environment variables in the `.env` file.

```bash
nano .env
```

Finally, if docker is installed, we can run the bot with the following command:

```bash
docker-compose up -d
````

Then follow the logs to assert that the bot is running:

```bash
docker-compose logs -f
```

## License

The project is licensed under the GNU General Public License v3.0. For more information, see the [LICENSE](LICENSE) file.
