# Robo Banana

Made for [Woohoojin](https://twitch.tv/woohoojin).

A highly robust Discord management bot with a featureset designed around content creation and entertainment.

Hosted on [Digital Ocean](https://m.do.co/c/4ec28adf00bb)

Knowers only.

---
- [Robo Banana](#robo-banana)
- [How To Run The Bot Locally](#how-to-run-the-bot-locally)
  - [Discord](#discord)
    - [Create our own server](#create-our-own-server)
    - [Adding Roles](#adding-roles)
    - [Enable Developer mode](#enable-developer-mode)
    - [Create an Application](#create-an-application)
      - [General Information](#general-information)
      - [OAuth2](#oauth2)
      - [Bot](#bot)
  - [Linux](#linux)
    - [Your local Environment](#your-local-environment)
    - [Python Virtual Environment](#python-virtual-environment)
      - [Using the "venv"](#using-the-venv)
      - [Requirements](#requirements)
    - [Additional Requirements](#additional-requirements)
      - [Useful Podman Commands](#useful-podman-commands)
      - [Mysql via Podman](#mysql-via-podman)
      - [Redis via Podman](#redis-via-podman)
      - [Check the status of the containers](#check-the-status-of-the-containers)
  - [VSCode](#vscode)
  - [Required Code changes](#required-code-changes)
    - [Config.ini required values](#configini-required-values)
      - [Required Source Code Changes](#required-source-code-changes)
  - [Server slash (/) commands.](#server-slash--commands)
    - [Update Script](#update-script)
  - [Run the bot](#run-the-bot)
    - [Starting the actual bot](#starting-the-actual-bot)
      - [Command line](#command-line)
      - [VSCode Debugging](#vscode-debugging)
---

# How To Run The Bot Locally
If you are comfortable with using git, python, and pip then a number of these steps can be skipped.

## Discord
In this example we will be using the Discord desktop client.

### Create our own server
The first needed is a our own Discord server to run the bot against. 
- click the "+" symbol to add a new server.
- select "Create My Own".
- Click "For me and my friends".
- Give it a name.

[How do I create a server](https://support.discord.com/hc/en-us/articles/204849977-How-do-I-create-a-server-)

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

### Enable Developer mode
By enabling Developer Mode it will become much easier to find the required ID/Snowflakes required for the bot to run.
- Open "User Settings" in the client (this will look like a small cog next to your user)
- Advanced
- Toggle "Developer Mode" to On.

Now when right clicking on any element in the client you will be able to copy the ID/Snowflake.

### Create an Application
We need to create an application by going to the following link in a web browser. [Create Application](https://discord.com/developers/applications?new_application=true)

This will be the link between what we do in Discord and the code running locally.

After the application has been created we will be shown a new page with settings.

#### General Information
There is nothing we need to do on this page, but take note of the **Application ID** as this will be needed later.

#### OAuth2
Select the `URL Generator` sub menu.
- On 'Scopes' select the tick boxes 
  - `applications.commands`
  - `bot`
- On Bot permissions select
  - `Administrator`
If you do not want to give your bot full Admin rights then you can tailor the scope to what you want and need. However as this is for development purposes I chose the above for ease.

Copy the `Generated URL` in to a browser window to invite the application to your server.

#### Bot
Under this heading we need to do a few things.
- "Reset Token" (You will only get one opportunity to copy this token, so sage it somewhere safe.)
- "Privileged Gateway Intents" (As this is for development and not production I enabled all three intents.)

## Linux
The following steps will also be able to be completed on a Windows machine, however the commands may differ slightly. If you use a Windows desktop for development you will need to find the correct commands to run.

[Clone the repository to your local machine](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)

If you are looking to contribute to the project then it is best to [fork the repository](https://docs.github.com/en/get-started/quickstart/fork-a-repo). You will need to ensure that it is kept up to date with the main repo, unless you want to diverge from the project.

### Your local Environment
Now that we have the code saved to our local machine we can change directory into that folder in your terminal.

When in the correct directory if you list files you should see
```bash
[RoboBanana]$ ls
bot.py  commands config.ini.example  config.py  controllers  db  README.md  requirements.txt  Robot.png  server  startServer.sh  views
```

### Python Virtual Environment
In the root of the project directory run the command
``` bash
[RoboBanana]$ python -m venv .venv
```
This will create a new virtual environment (venv) inside of the directory .venv

#### Using the "venv"
```bash
[RoboBanana]$ source .venv/bin/activate
```
The venv can be deactivated by typing `deactivate` in the terminal.

#### Requirements
With the venv active install the requirements
```
pip install -r requirements.txt
```

### Additional Requirements
For the bot to run locally you will need both a MySQL/MariaDB server and a Redis Cluster.

I would recommend using Docker or Podman for this for ease of development.

#### Useful Podman Commands
- `podman ps` (Shows running containers)
- `podman ps --all` (Shows all containers including failed and stopped)
- `podman stop <container name or id>`
- `podman start <container name or id>` (useful if you have restarted your pc)
  
#### Mysql via Podman
- Create a directory for the database
- If selinux is active `sudo semanage fcontext -a -t container_file_t <path to directory>`
- `sudo restorecon -Rv <path to directory>`
- `podman pull mysql:latest`
- Run the container using the command
```
podman run -d \
--name mysql \
-p 3306:3306 \
-v <DATA DIR FROM ABOVE COMMAND>:/var/lib/mysql \
-e MYSQL_ROOT_PASSWORD='MyStr0ngP@ssw0rd' \
-e MYSQL_USER=dbuser1 \
-e MYSQL_PASSWORD='dbuser1password' \
-e MYSQL_DATABASE=testdb \
mysql:latest
```

#### Redis via Podman
- Create a directory for Redis storage
- If selinux is active `sudo semanage fcontext -a -t container_file_t <path to directory>`
- `sudo restorecon -Rv <path to directory>`
- `podman pull redis:latest`
- Run the container using the command
```
podman run -d \
--name redis_server \
-v <DATA DIR FROM ABOVE COMMAND>:/var/redis/data \
-p 6379:6379 \
redis
```
#### Check the status of the containers
When running `podman ps` you should see something similar to below. This means both MySQL and Redis are running.
```bash
[RoboBanana]$ podman ps 
CONTAINER ID  IMAGE                           COMMAND       CREATED     STATUS          PORTS                   NAMES
bddcee023ff4  docker.io/library/mysql:latest  mysqld        3 days ago  Up 7 hours ago  0.0.0.0:3306->3306/tcp  mysql
c224b47402ea  docker.io/library/redis:latest  redis-server  3 days ago  Up 7 hours ago  0.0.0.0:6379->6379/tcp  redis_server]
```

## VSCode
You can use any IDE, my choice is [VSCode](https://code.visualstudio.com/)

In VSCode when opening the folder where you've saved the bot code it should recognise that you have a .venv directory and ask if you would like to use this as the interpreter. Choose Yes.

If you don't get this prompt you can [manually select the interpreter](https://code.visualstudio.com/docs/python/environments)

When running the bot you can either manually run it from the termainal using `python ./bot.py` if you add a launch config in vscode we can start a debug session and take advantage of breakpoints.

An example launch.json can be found in the examples folder. This needs to be copied to the root path of the bot code in a directory called '.vscode'. `ROBOBANANA/.vscode/launch.json`

## Required Code changes
The first thing that we need to do is set up the `config.ini` file.
Copy `config.ini.example ` to the same directory removing the '.example' part.

### Config.ini required values
`Token`: This is the token you saved when creating an application.

Anything ending in Channel, or ChannelID will need an ID/Snowflake of a channel. For my personal development I have set this to the value of the default 'General' channel.

With Developer Mode on simply right click the channel name and select **Copy Channel ID**

`BotRoleID`: Go to Roles, you should see a role there with your bots name. right click the role name and copy ID.

`GiftedTier#RoleID and Tier#RoleID`: As above but now with the relevant role id. I used the same ID for the gifted and standard Tier, but if you like you can create more roles for each value.

`ModRoleID`: ID for the mod role.

`GuildID`: Right click your server/server name **Copy Server ID**

Use this same ID for both **GuildID** entries

`MySQL`: Replace the values with what you set when running your mysql server
```
[MySQL]
Username = dbuser1
Password = dbuser1password
Host = 0.0.0.0:3306
Name = testdb
```

#### Required Source Code Changes
At time of writing there are a few hard coded values in the file **controllers/sub_controller.py** that needs to be updated to enable the bot to run.

**Line 42**: Update this to be a valid role on your server.

**Lines 123/124/125**: As above update these to be valid role IDs

**Lines 128/129**: Update these IDs to be valid channel IDs from your server.

## Server slash (/) commands.
[Slash Command Documentation](https://discord.com/developers/docs/interactions/application-commands)

To register custom slash commands with the server you will need to interact with the discord API. In the examples folder there is an example script which will create a / command for creating a prediction.

### Update Script
- `Application ID`: You can get this ID from the General Information page when creating the application
- `GUILD ID`: This is the same ID from the config.ini
- `TOKEN`: The same token used in the config.ini

## Run the bot
Ensure both the MySQL and Redis instances are still running
```bash
podman ps
```
Make sure you have activated the python venv
```bash
[RoboBanana]$ source .venv/bin/activate
```
Start the hypercorn server
```bash
[RoboBanana]$ ./startServer.sh
```
You'll see output like:
```bash
2023-08-26 22:20:32 INFO     apscheduler.scheduler Adding job tentatively -- it will be properly scheduled when the scheduler starts
2023-08-26 22:20:32 INFO     apscheduler.scheduler Added job "keep_alive" to job store "default"
2023-08-26 22:20:32 INFO     apscheduler.scheduler Scheduler started
2023-08-26 22:20:32 INFO     discord.client logging in using static token
[2023-08-26 22:20:32 +0100] [46277] [INFO] Running on http://0.0.0.0:3000 (CTRL + C to quit)
2023-08-26 22:20:32 INFO     hypercorn.error Running on http://0.0.0.0:3000 (CTRL + C to quit)
2023-08-26 22:20:33 INFO     discord.gateway Shard ID None has connected to Gateway (Session ID: ba8b122009a7d9aaa2c387f51f43ab84).
2023-08-26 22:20:35 INFO     server.util.discord_client Logged in as my_robobanana#5138 (ID: 1143616097560580116)

```

### Starting the actual bot
#### Command line
If you want to just run the bot and watch for logs without using breakpoints to step through. You can open a new terminal and simply run:
```
[RoboBanana]$ python bot.py
```
#### VSCode Debugging
If you would like to use VSCode debugging and have copied the launch config file from previous steps or have your own then you can click the icon on the left that looks like a small bug on top of a play symbol.

Finally click the play symbol at the top of the new pane with the words RoboBanana next to it.

You'll see a terminal in VSCode open showing the bot activate and start listening for commands.
```bash
RoboBanana]$ source RoboBanana/.venv/bin/activate
(.venv) [RoboBanana]$  /usr/bin/env RoboBanana/.venv/bin/python .vscode/extensions/ms-python.python-2023.14.0/pythonFiles/lib/python/debugpy/adapter/../../debugpy/launcher 48971 -- RoboBanana/bot.py 
2023-08-26 22:31:09 WARNING  discord.client PyNaCl is not installed, voice will NOT be supported
2023-08-26 22:31:09 INFO     discord.client logging in using static token
2023-08-26 22:31:10 INFO     discord.gateway Shard ID None has connected to Gateway (Session ID: 6bc608b4de3f9ede5868f1818af8093b).
2023-08-26 22:31:12 INFO     root Logged in as my_robobanana#5138 (ID: 1143616097560580116)
2023-08-26 22:31:12 INFO     controllers.temprole_controller [TEMPROLE TASK] Running expire roles...
```