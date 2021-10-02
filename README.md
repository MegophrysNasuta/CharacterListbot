# Achaea Character Listing Bot for command line and Discord

## Installation

1. Follow [these instructions](https://discordpy.readthedocs.io/en/stable/discord.html#discord-intro) to create a bot and add it to your Discord.
2. Make sure you have Python3 and pipenv (`python3 -m pip install --user pipenv`) installed.
3. Set an environment variable called `ACHAEA_WHOBOT_TOKEN` to your token (e.g. `export ACHAEA_WHOBOT_TOKEN=asdfaisodhgoafoisuheaoiughoweiaghwe`).
4. Run `pipenv run python dbot.py`

If it says "Ready!" it should be accepting commands as your bot user!

## Usage

 - `!honors`/`!whois` <CharacterName>
 - `!who`/`!qw`/`!qwho`/`!online`
 - `!namestats` -- see how over-represented A names are today
 - `!math` -- a little arithmetic calculator

### Polls

You can start a poll with `!poll what's the meaning of life?`. The bot will
post your question and an ID you can use to interact with the poll. If you
start your poll with `!poll stingy` then only you can add options with
emoji, and your votes don't count. An open poll lets anyone add options and
counts all votes.

When an option is added to a poll, the bot will also report its ID in 
channel. This can be used in conjunction with `!setpollopt ID meaning` to
clarify what the emoji is meant to represent.

All of this information is presented when you view the results with
`!pollreport ID`.

## Host it on Heroku

1. Get a Heroku account and set up an app. Install the Heroku CLI tools.
2. `heroku git:remote -a your_app_name` in this repository's folder.
3. `heroku config:set ACHAEA_WHOBOT_TOKEN=your_bots_token` (or do this in the Heroku UI under Settings for your app).
4. `git push heroku main` and it should be running.
5. I recommend installing the Heroku Scheduler addon and scheduling `python clist.py update` to run every 10 minutes. This keeps things from getting out of date and also keeps your free dyno awake!
6. (Optional) Set up a Heroku Postgres hobby add-on. Usage will be automatic but it would currently be up to you to occasionally clean it out if you were trying to keep it under 100k rows (free tier). It will take a very, very long time to get to there, though.
