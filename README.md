# Raffle Bot

Discord bot that can be used to run raffles!

## Raffles

The bot supports three kinds of raffles.

### `Normal` Raffle

The `normal` raffle is probably the one you'll want to use... normally.

Once someone wins a normal raffle, they become ineligible to win for the next *five* (5) raffles OR *one week* whichever is **longer**.

Winners are selected based on weighted odds. The more raffles someone has won in the past, the lower their chances are of winning a future one. Details on the weighted selection are below.

This is to really ensure fairness since *true randomness* does not guarantee anything resembling an even distribution of wins.

### `New` Raffle

The `new` raffle is restricted to only people who have never won a raffle before.

Winner selection is unweighted. Everyone who enters has an equal chance of winning.

### `Anyone` Raffle

The `anyone` raffle has zero restrictions on it AND wins are **not** recorded (meaning it will not affect future `normal` or `new` raffles).

Winner selection is also unweighted. Everyone who enters has an equal chance of winning.

### tl;dr

- `Normal` raffle: can't win again after a recent win and future odds are decreased with each win
- `New` raffle: only people who've never won can win
- `Anyone` raffle: anyone can win

## Usage

### Start a Raffle

```bash
!raffle start
```

Only one raffle may be active at a time per guild.

### Enter a Raffle

Members enter by reacting to the message sent by the bot. They can use any emoji they want.

The bot will only enter in each user once (no matter how many times they reacted).

### End a Raffle

```bash
!raffle end <type=normal> <winners=1>
```

To pick a winner, use the `!raffle end` command.

To change the type of raffle, supply either `normal` (default), `new`, or `anyone` as the first argument. Default: `normal`

To change the number of winners, include the number as the second argument. Default: `1`

Note that if you want to change the winners in a `normal` raffle, you do still need to include the word `normal`.
e.g. `!raffle end normal 5`

### Redo a Raffle

```bash
!raffle redo <type=normal> <winners=1>
```

If a winner needs to be re-drawn from an already-closed raffle, **reply to the original raffle message** (from the bot) and use the `!raffle redo` command.

This is mostly equivalent to the `end` command but you must specify which raffle's entrants to use for the new draw.

The old winner(s) of the raffle being redone will be erased. So if it was their first win, they will be eligible once again.

### Examples

```bash
!raffle start # Start a new raffle
!raffle end # End a normal raffle with 1 winner
!raffle end normal 5 # End a normal raffle with 5 winners
!raffle end new # End a new raffle with 1 winner
!raffle end anyone 2 # End an enyone raffle with 2 winners
```

Remember `redo` is the same as `end` except you send the command in reply to the bot's start message.

### Screenshot

![Example screenshot](https://i.imgur.com/X1BlPGJ.png)

## Data Storage

This bot stores as little data as possible.
The table schema should be clear about what is actually stored but to make it clear:

`raffles`:
- `guild_id` -- The Discord server ID
- `message_id` -- The actual message the bot sent to start the raffle

`past_wins`:
- `id` -- Simple auto-incrementing ID
- `guild_id` -- The Discord server ID
- `message_id` -- The message the bot sent to start the raffle
- `user_id` -- The winner of that particular raffle

Other than the user ID there is no personal information otherwise stored or logged.

For raffle fairness, past wins are stored and *never purged*. These are preserved even after leaving the server in order to prevent cheating by leaving and re-joining.
If you would like your past wins expunged, please contact the server owner.

Still TODO is a consent flow that will only allow you to win raffles if you have agreed to these terms.

## Weighted Odds

Each time someone wins a raffle, their odds of winning a subsequent raffle are decreased by 25%.

You can conceptually think of this as giving out fewer "tickets" to enter the raffle each time you win.

Someone who has won once is only 75% as likely to win as someone who has never won.
Someone who has won twice is 56% (75% * 75%) as likely to win as someone who has never won.
The odds compound the greater the number of wins between two people is.

The full algorithm in code [can be found here](https://github.com/iamlawfulgood/raffle_bot/blob/b67af5377bdec0aa9d503e475410d4474ed8a69a/bot.py#L197-L305).

It's important to note that these are all RELATIVE odds. Meaning they are dynamic depending not only on the number of times you've won but also on the other people who have entered the raffle along with you.

So, for example, if a raffle's entrants are all people who've won once before, they all have an equal chance of winning this one.

It's also worth noting that the past wins are currently fixed forever. Potentially this will be ajusted in the future to e.g. only consider wins in the past year. But this is NOT the case at present.

## Installation

### Configuration

Create a new `config.ini` file.
```bash
$> cp config.ini.schema config.ini
```

Then add your bot account's token to the `config.ini`.

### Build and Run
```bash
$> docker-compose build
$> docker-compose up -d
```

## Discord Server Setup

The "raffler" role will need to be created and assigned to any members that should be allowed to manage raffles.
