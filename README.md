Made for [Woohoojin](https://twitch.tv/woohoojin).


# RoboBanana
RoboBanana is a simple Twitch/Discord bot for managing and redeeming channel rewards using channel points.

## Features
Redeemable channel rewards with point cost and name.
Pending rewards that can be completed or refunded by moderators.
Automatic reward redemption with no need for a moderator to manually complete a reward.
Technologies


## Installation
To run RoboBanana, you will need to create a config.ini file in the root directory and fill in the values exampled in the congif.ini.example

###After setting up the .ini file, you can install the necessary Python packages using:

pip install -r requirements.txt

Run the bot using:
python bot.py


## Usage
### Commands
### Mod Commands
    sync: This command can be used to synchronize the database with any external system, ensuring that all data is up-to-date.

    gift: This command is used to gift a reward or points to a user.

    start: This command can be used to start a new raffle, prediction, or any other similar activity.

    end: This command can be used to end a raffle, prediction, or any other similar activity.

    add_reward: This command is used to add a new reward to the system.

    remove_reward: This command can be used to remove a reward from the system.

    allow_redemptions: This command can be used to enable the redemption of rewards.

    pause_redemptions: This command can be used to pause the redemption of rewards.

    check_redemption_status: This command can be used to check the status of a reward redemption.

    start_prediction: This command can be used to start a new prediction.

    refund_prediction: This command can be used to refund a prediction.

    payout_prediction: This command can be used to payout a prediction.

    redo_payout: This command can be used to redo a payout.

    give_points: This command can be used to give points to a user.

    good_morning_count: This command can be used to count the number of times a user has said "good morning" in a channel.

    good_morning_reward: This command can be used to reward a user for saying "good morning" a certain number of times in a channel.

    good_morning_reset: This command can be used to reset the "good morning" count for a user.

    good_morning_increment: This command can be used to increment the "good morning" count for a user.

    remove_raffle_winner: This command can be used to remove a winner from a raffle.

### User Commands

    redeem_reward: This command allows a user to redeem an available channel reward. It first checks if reward redemptions are allowed, and if not, it sends a message indicating that redemptions are currently paused. If redemptions are allowed, it retrieves the available rewards and the user's current point balance from the database, and sends a RedeemRewardView containing the rewards and point balance to the user.

    list_rewards: This command lists all the available channel rewards. It retrieves the rewards from the database and constructs a message string with the name and point cost of each reward. It then sends this message to the user.

    point_balance: This command allows a user to check their current number of channel points. It retrieves the user's point balance from the database and sends a message indicating the user's current point balance to the user.

    bet: This command allows a user to place a bet on the currently ongoing prediction. It takes two arguments: choice and points. Choice is the user's chosen PredictionChoice (either A or B), and points is the number of channel points the user wants to bet. It then creates a new prediction entry in the database with the user's bet, choice, and interaction ID, and sends a message confirming that the user's vote has been cast.

    good_morning: This command allows a user to say "good morning" in a designated channel. It accrues "good morning points" for the user, and sends a message acknowledging the user's good morning.

    good_morning_points: This command allows a user to check their current number of "good morning points". It retrieves the user's good morning points from the database and sends a message indicating the user's current good morning points to the user.

### Manager Commands 

    flag_vod: Flags a VOD (video on demand) as approved, rejected, or complete. It takes one argument vod_type which is of type VODType (an enum with three possible values - approved, rejected, or complete). The command can only be executed by users with the "Community Manager" role. 




## Project Structure
### The project is structured as follows:

    commands/: This directory contains files defining all the bot's commands, separated by role.

    controllers/: This directory contains files defining the business logic of the bot. Each controller could be responsible for handling a specific feature or set of related features, such as managing points or handling predictions. 

    db/: This contains the models files, as described. The models.py file defines the schema for the bot's database tables. This folder also includes the interactions for the database for other files to use.

    views/: Contains the view classes used to render Discord components.
        
    config.py: Contains the configuration values loaded from the .ini file.

    bot.py: Contains the main bot code.

    requirements.txt: Contains the list of required Python packages.

RoboBanana is currently limited to a single Discord server and Twitch channel.

Hosted on [Digital Ocean](https://m.do.co/c/4ec28adf00bb)

Knowers only.
