# Robo Banana

Made for [Woohoojin](https://twitch.tv/woohoojin).

A highly robust Discord management bot with a featureset designed around content creation and entertainment.

Hosted on [Digital Ocean](https://m.do.co/c/4ec28adf00bb)

Knowers only.

---
- [Robo Banana](#robo-banana)
- [How To Run The Bot Locally](#how-to-run-the-bot-locally)
  - [Discord](#discord)
    - [Create your own server](#create-your-own-server)
    - [Enable Developer mode](#enable-developer-mode)
    - [Adding Roles](#adding-roles)
    - [Create an Application](#create-an-application)
    - [Python Virtual Environment](#python-virtual-environment)
    - [Requirements](#requirements)
      - [MySQL](#mysql)
      - [Redis](#redis)
  - [Required Code changes](#required-code-changes)
    - [Config.ini required values](#configini-required-values)
  - [Server slash (/) commands.](#server-slash--commands)
  - [Run the bot](#run-the-bot)
---

# How To Run The Bot Locally
These setup instructions outline the essential steps for initializing the bot and enabling it to respond to commands from Discord clients.

## Discord

### Create your own server
For development purposes it is required to have your own Discord server to test against. Setup your own server by following [this guide](https://support.discord.com/hc/en-us/articles/204849977-How-do-I-create-a-server-)

### Enable Developer mode
By enabling Developer Mode it will become much easier to find the ID/Snowflakes required for the bot to run.
- Open "User Settings" in the client (this will look like a small cog next to your user)
- Advanced
- Toggle "Developer Mode" to On.

Now when right clicking on any element in the client you will be able to copy the ID/Snowflake.

### Adding Roles
For the bot to run there are a minimum of 4 roles needed.
- Click your server name in the upper-left corner of your server.
- Go to Server Settings > Roles.
- Click Create Role.
  - Mod (give this one administrator permissions)
  - tier1
  - tier2
  - tier3

You will also need to add yourself as a member to all 4 roles. Mod must have a capital M.

### Create an Application

To create an Application which is required to link Discord to your local code follow Step 1 from [this guide](https://discord.com/developers/docs/getting-started). Steps 2 and 3 are not required for this setup.


### Python Virtual Environment
We highly recommend you setup a venv to ensure that your RoboBanana environment is isolated from other projects you may be working on. [Creation of virtual environments](https://docs.python.org/3/library/venv.html)


### Requirements

With the venv active install the requirements
```
pip install -r requirements.txt
```

You will also need MySQL and Redis for RoboBanana to connect to. This can be accomplished a number of ways. Reference one of the tutorials below:

#### MySQL
- [Installing MySQL to your Operating System](https://dev.mysql.com/doc/mysql-installation-excerpt/5.7/en/)
- [Running MySQL using Docker](https://hub.docker.com/_/mysql)

#### Redis
- [Installing Redis to your Operating System](https://redis.io/docs/getting-started/installation/)
- [Running Redis using Doker](https://redis.io/docs/getting-started/install-stack/docker/)

## Required Code changes
Move or Copy the config.ini.example file to be config.ini

### Config.ini required values
`Token`: This is the token you saved when creating an application.

Anything ending in Channel, or ChannelID will need an ID/Snowflake of a channel. For ease of set up these can all be the same ID.

With Developer Mode on simply right click the channel name and select **Copy Channel ID**

`BotRoleID`: Go to Roles, you should see a role there with your bots name. right click the role name and copy ID.

`GiftedTier#RoleID and Tier#RoleID`: As above but now with the relevant role id for tiers.

`ModRoleID`: ID for the Mod role.

`GuildID`: Right click your server/server name **Copy Server ID**

Use this same ID for both **GuildID** entries

`MySQL`: Replace the values with what you set when running your mysql server

## Server slash (/) commands.
[Slash Command Documentation](https://discord.com/developers/docs/interactions/application-commands)

To import the required slash commands for RoboBanana to work open the **bot.py** file and uncomment the following 4 lines;
```
# guild = discord.Object(id=GUILD_ID)
# tree.clear_commands(guild=guild)
# tree.copy_global_to(guild=guild)
# await tree.sync(guild=guild)
```

After running the bot for the first time it is important to stop the bot and comment the lines out again. If this is not done then you may become rate limited by Discord.

## Run the bot

- Start the hypercorn server
```bash
[RoboBanana]$ ./startServer.sh

2023-08-26 22:20:32 INFO     apscheduler.scheduler Adding job tentatively -- it will be properly scheduled when the scheduler starts
2023-08-26 22:20:32 INFO     apscheduler.scheduler Added job "keep_alive" to job store "default"
2023-08-26 22:20:32 INFO     apscheduler.scheduler Scheduler started
2023-08-26 22:20:32 INFO     discord.client logging in using static token
[2023-08-26 22:20:32 +0100] [46277] [INFO] Running on http://0.0.0.0:3000 (CTRL + C to quit)
2023-08-26 22:20:32 INFO     hypercorn.error Running on http://0.0.0.0:3000 (CTRL + C to quit)
2023-08-26 22:20:33 INFO     discord.gateway Shard ID None has connected to Gateway (Session ID: ba8b122009a7d9aaa2c387f51f43ab84).
2023-08-26 22:20:35 INFO     server.util.discord_client Logged in as my_robobanana#5138 (ID: 1143616097560580116)

```

Initiate an instance of the Bot:
```bash
[RoboBanana]$ python bot.py

2023-08-27 13:08:19 WARNING  discord.client PyNaCl is not installed, voice will NOT be supported
2023-08-27 13:08:19 INFO     discord.client logging in using static token
2023-08-27 13:08:20 INFO     discord.gateway Shard ID None has connected to Gateway (Session ID: d34b64a9793cadc830aecd6870fa4289).
2023-08-27 13:08:22 INFO     root Logged in as my_robobanana#5138 (ID: 1143616097560580116)
2023-08-27 13:08:22 INFO     controllers.temprole_controller [TEMPROLE TASK] Running expire roles...
```
