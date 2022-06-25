#!/usr/bin/env python
import ast
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import logging
import operator as op
import os
import random
import re
import string
import sys

from dateutil.parser import parse as parse_date
import discord

from clist import *


client = discord.Client()

SECRET_WORD_BANK = (
    "Deucbless",
    "lmao",
    "wooo",
    "kitty",
    "Penwize",
    "clown",
    "rory",
    "Nicola",
    "cyrene",
    "Aurora",
    "targ",
    "raiding",
    "bitch",
    "cake",
    "shrub",
    "weed",
    "high",
    "vape",
    "stoned",
    "scimitar",
    "wtf",
    "god damn",
    "cossi",
    "goat",
    "pool",
    "dick",
    "sucks",
    "vesyra",
    "boris",
    "britain",
    "romaen",
    "yayy",
    "sexy",
    "liquor",
    "drunk",
    "alyzar",
    "kez",
    "character",
    "mark",
    "veldrin",
    "iaxus",
    "cat",
    "noo",
    "bean",
    "xd",
    "contract",
    "salad",
    "huge",
    "cheese",
    "hungry",
    "incredible",
    "bugs",
    "pariah",
    "amranu",
    "block",
    "achaea",
    "bloodsworn",
    "crusade",
    "fuck",
    "shit",
    "damn",
    "ugh",
    "penis",
    "serp serp",
    "dawnlord",
    "dawnlady",
    "lumarch",
)


def secret_word():
    if getattr(secret_word, "__word", None) is None or random.random() < 0.55:
        secret_word.__word = random.choice(SECRET_WORD_BANK)

    return secret_word.__word.lower()


CITY_WHO_REGEX = re.compile(
    "\!(?P<city>mhaldor|hashan|ashtan|eleusis|targossas|cyrene|rogues|intents)"
)
DICE_ROLLING_REGEX = re.compile("\!roll (?P<number>\d*)d(?P<die_type>\d+)")
SET_POLLOPT_REGEX = re.compile("\!setpollopt (?P<pollopt_id>\d+) (?P<meaning>.*)")
POLL_REGEX = re.compile("\!poll(?P<stingy> stingy)? (?P<question>.*)")
POLL_OPEN_REGEX = re.compile("^Poll (?P<poll_id>\d+)")
REMINDER_REGEX = re.compile('\!remind( me)?( to)? "(?P<what>.*)" (?P<when>.*)')


ERP_CITIES = ("(none)", "cyrene", "hashan")


coney_islandisms = (
    "**FK YA LIFE! BING BONG!**",
    "Real, son, we keep it real!",
    "Ayo Ariana Grande, wassup mama? Come to Coney Island, take a spin on the Cyclone! ... I miss you",
    "I have Seven. Female. Wives. Go to my Instagram!",
    "'Sup, baby? Take me out to dinner...",
    "Hey, Kim ain't got Sht. On. Me.",
    "Yo, he got his phone in his balls. Steve Jobs did NOT die for this.",
    "Hey, you see these dogs in your front yard? Just know upstairs I'm goin' hard. BING BONG",
    "Who's the president? *BYRON!* Who? **BYRON!!** Say wassup to Byron: **WASSSSSUUUUPPPP BBBYYYYRRRRROOONNNNNN**",
    "I'm the Boardwalk King.",
    "We doin' things right, you hear me? We knock these grandmothers off their fkn skates, you heard? BING BONG",
    "_*knocks hat*_ If you see this hard hat at your crib, heh, just know I'm in her ribs, you hear me?",
    "JOE BYRON, HERE I AM, I AM NOBODY, BUT I AM SOMEBODY IN THE LORD. **JESUS CRISTOOOOOOOOO**",
    "If I'm tryin' to tell you one thing this summer, don't die for free. Don't die. Not for free, you heard?",
    "What you do? *PAIN!* What? **PAIN!!** What's your name? **P̹Ḁ̴̳̩͍͙I͙̱̘͚̻͍̫N̖!̗!͎͈̤͔̼̮͡**",
)


math_operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.BitXor: op.xor,
    ast.USub: op.neg,
}


def eval_(node):
    if isinstance(node, ast.Num):  # <number>
        return node.n
    elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
        return math_operators[type(node.op)](eval_(node.left), eval_(node.right))
    elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
        return math_operators[type(node.op)](eval_(node.operand))
    else:
        raise TypeError(node)


def eval_expr(expr):
    """
    >>> eval_expr('2^6')
    4
    >>> eval_expr('2**6')
    64
    >>> eval_expr('1 + 2*3**(4^5) / (6 + -7)')
    -5.0
    """
    return eval_(ast.parse(expr, mode="eval").body)


def roll_dice(die_type, num_dice=None):
    die_type, num_dice = int(die_type), int(num_dice or 1)
    if num_dice > 1000:
        raise ValueError("That's too many dice! :hot_face:")

    if die_type == 0:
        return 0
    elif die_type == 1:
        return num_dice

    return sum((random.randint(1, die_type) for _ in range(num_dice)))


def stUdLYcApS(s):
    result = []
    for char in s:
        if random.randint(1, 2) % 2 == 0:
            result.append(char.upper())
        else:
            result.append(char.lower())
    return "".join(result)


@client.event
async def on_ready():
    while True:
        wild_out = random.randint(1, 250)
        if wild_out > 249:
            targ_server = client.get_guild(int(os.environ["DISCORD_TARG_SERVER"]))
            if targ_server is None:
                raise RuntimeError("DISCORD_TARG_SERVER not found")

            bot_stuff = targ_server and targ_server.get_channel(
                int(os.environ["DISCORD_TARG_BOT_CHANNEL"])
            )
            if bot_stuff is None:
                raise RuntimeError("DISCORD_TARG_BOT_CHANNEL not found")

            if bot_stuff:
                wild_shit = list(coney_islandisms)
                wild_shit.extend(
                    [
                        "Can't you make a tattoo gun out of a PS2 controller?",
                        ":rainboweggplant:",
                        ":Deucbless:",
                        "Alyzar kinda looks nice today. Huh.",
                        "Stick",
                        "What if capitalism supplied the drug trade lmfao",
                        "straight up fuck you unlegal states",
                        "I am going outside, please pray for my safety :pray:",
                        "D:",
                        "brah",
                        "^",
                        "gottem",
                        "You just get string, tie it to a chicken leg, and find a shallow inlet",
                        "Even the samurai have teddy bears, and even the teddy bears get drunk",
                    ]
                )
                await bot_stuff.send(random.choice(wild_shit))

        ## TEMPORARY - PURGE USER
        # targ_server = client.get_guild(int(os.environ['DISCORD_TARG_SERVER']))
        # if targ_server is None:
        #    raise RuntimeError('DISCORD_TARG_SERVER not found')

        # authored_by_target_user = lambda msg: str(msg.author) == 'vsblackflame#5313'
        # for channel in targ_server.channels:
        #    if not hasattr(channel, 'purge'): continue
        #    logging.critical('Purging channel %s', channel.name)
        #    deleted = (None,)
        #    while len(deleted) > 0:
        #        try:
        #            deleted = await channel.purge(limit=100,
        #                                          check=authored_by_target_user)
        #        except discord.errors.Forbidden:
        #            logging.critical('Cannot purge %s.', channel.name)
        #            break
        #        else:
        #            logging.critical('%i purged.', len(deleted))

        #    two_weeks_ago = datetime.today() - timedelta(days=13)
        #    try:
        #        logging.critical('Expunging historical messages in %s', channel.name)
        #        async for msg in channel.history(limit=None, before=two_weeks_ago):
        #            if authored_by_target_user(msg):
        #                await msg.delete()
        #    except discord.errors.Forbidden:
        #        logging.critical('Cannot purge %s.', channel.name)
        ## PURGE USER CODE ENDS

        await asyncio.sleep(1800)


@client.event
async def on_reaction_add(reaction, user):
    if reaction.message.author != client.user:
        return

    async def set_pollopt(with_vote=False):
        emoji = reaction.emoji
        args = create_pollopt(matches["poll_id"], emoji, emoji, user.id, with_vote)
        msg = "Poll option %i belonging to  poll %i is now %s"
        await reaction.message.channel.send(msg % (args + (emoji,)))

    matches = POLL_OPEN_REGEX.match(reaction.message.content)
    if matches:
        if reaction.count == 1:
            if is_poll_locked(matches["poll_id"]):
                poll_owner = get_poll_owner(matches["poll_id"])
                if str(user.id) == poll_owner:
                    await set_pollopt()
                else:
                    reaction.remove(user)
            else:
                await set_pollopt(with_vote=True)
        else:
            adjust_pollopt_vote(reaction.emoji, reaction.count)


@client.event
async def on_reaction_remove(reaction, user):
    if reaction.message.author != client.user:
        return

    matches = POLL_OPEN_REGEX.match(reaction.message.content)
    if matches:
        adjust_pollopt_vote(reaction.emoji, reaction.count)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    msg = []
    content = message.content.lower()
    crazy_word = secret_word()
    if content.startswith("!help") or content.startswith("!commands"):
        me = client.user.name.title()
        help_commands = {
            ("Ask %s" % me): "@%s will it rain today?" % me,
            "!bingbong": "!bingbong",
            ("!cuddle %s" % me): "!cuddle %s" % me,
            "!<city>": "!mhaldor",
            "!deathsights": "!deathsights <optional name>",
            "!dragons": "!dragons (or !who matters more)",
            "!givecaketo": "!givecaketo <name>",
            "!honors": "!honors <name>",
            "!honours": "!honours <name>",
            "!kdr": "!kdr <name> <optional name>",
            "!killsights": "!killsights <optional name>",
            "!logosians": "!logosians (or !who matters)",
            "!math": "!math (3 + 5) * 8 / 3",
            "!namestats": "!namestats (or !namestats offline)",
            ("!pet %s" % me): "!pet %s" % me,
            "!qw": "!qw",
            "!roll": "!roll 3d6",
            "!whois": "!whois <name>",
            "!who": "!who [for KDR try !who fucks and !who sucks]",
        }
        for cmd, tryit in help_commands.items():
            msg.append("%s TRY IT: %s" % (cmd.ljust(20), tryit))
        msg.append("\nPlus over 20 hidden commands and easter eggs.")
    elif content.startswith("!honours"):
        taunt_the_uk = (
            stUdLYcApS(content),
            "TEAM AMERICA, F**K YEAH! :flag_us::flag_us::flag_us:",
            "Is this Romaen??",
            "IT'S HONORS, BABY!! WOOOOO!!!! *\*fires machine gun into air\**",
            "I don't have to listen to this British crap.",
            "Rejoin the EU, already. What are y'all doing over there?",
            """
:flag_gb:                    :flag_gb:           :flag_gb: :flag_gb:
:flag_gb::flag_gb:       :flag_gb:       :flag_gb:          :flag_gb:
:flag_gb:      :flag_gb: :flag_gb:       :flag_gb:          :flag_gb:
:flag_gb:                    :flag_gb:           :flag_gb: :flag_gb:
            """,
            "https://media.giphy.com/media/9uIwMPlSoEr8NOwUdu/giphy.gif",
            "https://media.giphy.com/media/443jI3kpgOKfAfKxqo/giphy.gif",
            "https://media.giphy.com/media/DpYzl5716vg52/giphy.gif",
            "https://media.giphy.com/media/j0GW2I35KnU5e5BT7L/giphy.gif?cid=ecf05e47vnq3lhoqsc1ut9x06y1tvnqh07yi3qfesdxenz5k&rid=giphy.gif&ct=g",
            "https://media.giphy.com/media/ZdxLZAMhQcaKbIGdug/giphy.gif?cid=ecf05e47dyuhhicefn0p2nak6v5dtia4i73jovj93sbnjp0g&rid=giphy.gif&ct=g",
            "https://media.giphy.com/media/NaA840F7VJSHS/giphy.gif?cid=ecf05e47h7sot76tf80g7mss1pj5ru8bpywo8rfr0ltxdc20&rid=giphy.gif&ct=g",
            "https://media.giphy.com/media/deSTGRBAr6TdkVEjCd/giphy.gif?cid=ecf05e478zcb8s57d8lxbjhm3pje0ixh0tmcr1sr2eet35mj&rid=giphy.gif&ct=g",
        )
        msg.append(random.choice(taunt_the_uk))
    elif content.startswith("!givecaketo"):
        animals_eating_cake = (
            "https://c.tenor.com/8XDWT07FYh0AAAAM/hamster-cake.gif",
            "https://c.tenor.com/mY2hkWe-0g4AAAAM/cat-slap.gif",
            "https://c.tenor.com/KD0PVJ8WJcAAAAAM/more-for-me-stealing-food.gif",
            "https://c.tenor.com/iXSKnxq5S74AAAAM/panda-happy.gif",
        )
        msg.append(random.choice(animals_eating_cake))
    elif content == "!swcheat" and str(message.author) == "vsblackflame#5313":
        msg.append(crazy_word)
    elif crazy_word in content.split():
        if crazy_word == client.user.name.lower() and random.random() < 0.65:
            msg.append(
                random.choice(
                    (
                        "that's me!",
                        "yup",
                        "that's my name. don't wear it out. :unamused:",
                        "hi",
                        "yo",
                    )
                )
            )
        else:
            msg.append(re.search(crazy_word, message.content, flags=re.IGNORECASE)[0])
    elif client.user in message.mentions and "?" in content:
        magic_8ballisms = (
            "Oh, yeah.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes, definitely.",
            "Yup",
            "As I see it, yes.",
            "Most likely.",
            "Outlook: Good.",
            "Yeah",
            "Signs point to yes.",
            "Uhhhhh :flushed:",
            ":smirk:",
            "Better not tell you now...",
            "Pffff",
            "Are you for real?",
            "Don't count on it.",
            "Um, no.",
            "Nope",
            "My sources say no.",
            "Outlook: Not so good.",
            "Very doubtful.",
            "[x] Doubt.",
        )
        msg.append(random.choice(magic_8ballisms))
    elif content.startswith("!bingbong"):
        msg.append(random.choice(coney_islandisms))
    elif content.startswith("!" + client.user.name.lower()):
        msg.append("That's my name. Don't wear it out.")
    elif content.startswith("!nasuta"):
        msg.append("What is that supposed to do?")
    elif (content.startswith("!pet ") or content.startswith("!cuddle ")) and (
        client.user.name.lower() in content or client.user in message.mentions
    ):
        msg.append("*rubs up against <@%s>'s leg*" % message.author.id)
    elif content.startswith("!math"):
        try:
            expr = content.split(None, 1)[1]
        except IndexError:
            msg.append("**MATH!!**")
        else:
            try:
                msg.append(eval_expr(expr))
            except ZeroDivisionError:
                msg.append("Ow. What just happened?")
            except (SyntaxError, TypeError):
                msg.append(
                    "Think of me like a small Casio. I think you need a TI-92 for that one."
                )
    elif (
        content.startswith("!whois")
        or content == "!leaves"
        or content.startswith("!honors")
    ):
        try:
            if content == "!leaves":
                name = "daerik"
            else:
                name = content.split(None, 1)[1]
        except IndexError:
            if content.startswith("!honors"):
                msg.append("Honors whom?!")
            else:
                msg.append("Who is what, man?!")
        except Exception as e:
            print("Error: ", str(e), file=sys.stderr)
            raise
        else:
            if name == "namino":
                msg.append(
                    "https://www.collinsdictionary.com/images/thumb/bush_132902558_250.jpg?version=4.0.187"
                )
            elif name in ("gesai", "kholio", "relaed"):
                msg.append(
                    "https://ask2.extension.org/file.php?key=a2oszltmvb6ti1a1tvqbxace8eadb9bs&expires=1610755200&signature=49316c42c6706af7475564e4129b6266e30ebaff"
                )
            else:
                data = None
                try:
                    data = search_toon_archive(name)
                except CharacterNotFound:
                    try:
                        api_url = API_URL.replace("achaea", "aetolia")
                        data = search_toon_archive(name, api_url=api_url)
                    except CharacterNotFound:
                        msg.append('"%s" is not real. You made that up.' % name.title())
                if data is not None:
                    fullname = data.pop("fullname")
                    msg.extend([fullname, "=" * len(fullname)])
                    msg.append(
                        "Level {level} {cls} in House {house} in {city}.".format(
                            level=data.pop("level", ""),
                            cls=data.pop("class", "").title() or "Aetolian",
                            house=data.pop("house", "").title() or "Aetoliadoesnthavehouses",
                            city=data.pop("city", "").title() or "some city in Aetolia",
                        )
                    )
                    msg.append(
                        (
                            "{name} has killed {d} Achaean denizens and " "{a} Achaean adventurers."
                        ).format(
                            name=name.title(),
                            d=expand_kills(data.pop("mob_kills", "0")),
                            a=expand_kills(data.pop("player_kills", "0")),
                        )
                    )
                    msg.append(
                        "{name} is Explorer Rank {e:,d} and XP Rank {x:,d}.".format(
                            name=name.title(),
                            e=int(data.pop("explorer_rank", data.pop("explore rank", "").replace("th", "").replace("st", "").replace("nd", "").replace("rd", ""))),
                            x=int(data.pop("xp_rank", data.pop("xp rank", "").replace("th", "").replace("st", "").replace("nd", "").replace("rd", ""))),
                        )
                    )
    elif POLL_REGEX.match(content):
        matches = POLL_REGEX.match(content)
        poll_id = create_poll(
            matches["question"], message.author.id, message.id, matches["stingy"]
        )
        question = matches["question"].title().replace("'S", "'s")

        if matches["stingy"]:
            cta = "Vote with the emoji on this post."
        else:
            cta = "Add emoji to the post to respond."

        msg.append("Poll %i:\n> %s\n\n%s" % (poll_id, question, cta))
    elif SET_POLLOPT_REGEX.match(content):
        matches = SET_POLLOPT_REGEX.match(content)
        ok = set_pollopt_meaning(
            matches["pollopt_id"], matches["meaning"], message.author.id
        )
        if ok:
            msg.append(
                'Poll option %(pollopt_id)s defined to be "%(meaning)s".' % matches
            )
        else:
            msg.append("No.")
    elif content.startswith("!pollreport"):
        try:
            _, poll_id = content.split(None, 1)
            poll_id = int(poll_id)
        except ValueError:
            msg.append("That's not a poll. You made that up.")
        else:
            report = get_poll_report(poll_id, message)
            msg.append("\n".join(report))
    elif REMINDER_REGEX.match(content):
        matches = REMINDER_REGEX.match(content)
        try:
            when = parse_date(matches["when"], fuzzy=True)
        except ValueError as e:
            msg.append(str(e))
        else:
            msg.append('Set reminder to "%s" for %s!' % (matches["what"], when))
    elif DICE_ROLLING_REGEX.match(content):
        matches = DICE_ROLLING_REGEX.match(content)
        try:
            result = roll_dice(matches["die_type"], matches["number"])
        except ValueError as e:
            msg.append(str(e))
        else:
            msg.append(str(result))
    elif content.startswith("!deathsight"):
        try:
            _, player = content.split(None, 1)
        except ValueError:
            msg.extend([death["description"] for death in show_game_feed()])
        else:
            player = player.title()
            result = show_death_history(corpse=player)
            if result["since"] is not None:
                msg.append(
                    (
                        "Since %s, the following deaths have been "
                        "recorded for %s:" % (result["since"], player)
                    )
                )
                msg.append("")
                for row in result["deaths"]:
                    msg.append("Deaths to %s: %i" % row[:2])
            else:
                msg.append("No deaths recorded for %s." % player)
    elif content.startswith("!kdr"):
        try:
            _, player, against = content.split(None, 2)
        except ValueError:
            against = None
            try:
                _, player = content.split()
            except ValueError:
                player = None
        kills, deaths = show_kdr(player, against)
        if not kills and not deaths:
            if against:
                if " " not in against:
                    against = against.title()
                msg.append("No records for %s vs %s." % (player.title(), against))
            else:
                msg.append("No records for %s." % player.title())
        else:
            if kills and not deaths:
                if against:
                    rpt_line = "%s is on a perfect %i-kill streak against %s!"
                    rpt_line %= (player.title(), kills, against.title())
                else:
                    rpt_line = "%s is on a perfect %i-kill streak!"
                    rpt_line %= (player.title(), kills)
            else:
                kdr = "%.2f" % (kills / deaths)
                if against:
                    if " " not in against:
                        against = against.title()
                    rpt_line = "%s has killed %s %i times and died %i times. KDR: %s"
                    rpt_line %= (player.title(), against, kills, deaths, kdr)
                else:
                    rpt_line = "%s has %i kills and %i deaths. KDR: %s"
                    rpt_line %= (player.title(), kills, deaths, kdr)

            msg.append(rpt_line)
    elif content.startswith("!killsights"):
        try:
            _, player = content.split(None, 1)
        except ValueError:
            msg.append("You have to tell me who you want to see kills for.")
        else:
            player = player.title()
            result = show_death_history(killer=player)
            if result["since"] is not None:
                msg.append(
                    (
                        "Since %s, the following kills have been "
                        "recorded for %s:" % (result["since"], player)
                    )
                )
                msg.append("")
                for row in result["kills"]:
                    msg.append("Killed %s: %i" % row[:2])
            else:
                msg.append("No kills recorded for %s." % player)
    elif CITY_WHO_REGEX.match(content):
        toons = list_toons()
        city = CITY_WHO_REGEX.match(content)["city"]
        translations = {"rogues": "(none)", "intents": "Tent City"}
        translate_city = lambda c: translations.get(c, c)
        if translate_city(city) in toons:
            if city == "rogues":
                msg.append("Literal Heathens:")
            elif city == "intents":
                msg.append("Beyond the edge of sanity:")
            else:
                msg.append("%s:" % city.title())
            key = translate_city(city)
            msg.append(", ".join(toons[key]))
            msg.append("")
            msg.append("%i online." % len(toons[key]))
        else:
            msg.append(
                random.choice(
                    (
                        "The lights are on but nobody's home. :thinking:",
                        "Nope.",
                        '"%s" is not real. You made that up.' % translate_city(city),
                        "https://media.giphy.com/media/1l7GT4n3CGTzW/giphy.gif",
                        "https://media.giphy.com/media/3ohjUXMSEIvIsVRmA8/giphy.gif",
                        "https://media.giphy.com/media/26hkhPJ5hmdD87HYA/giphy.gif",
                    )
                )
            )
    elif content.startswith("!who"):
        min_level = 1
        positive_kdr = None
        if content.endswith("matters"):
            min_level = 80
        elif content.endswith("matters more"):
            min_level = 100
        elif content.endswith("fucks"):
            positive_kdr = True
        elif content.endswith("sucks"):
            positive_kdr = False

        api_url = None
        if content.startswith("!whotolia"):
            api_url = API_URL.replace("achaea", "aetolia")
            toons = list_toons(
                min_level=min_level, api_url=api_url, positive_kdr=positive_kdr, quick=True
            )
            msg.append(", ".join(toons))
            total = len(toons)
        else:
            toons = list_toons(
                min_level=min_level, api_url=api_url, positive_kdr=positive_kdr
            )
            total = 0
            for city in sorted(toons):
                if city:
                    msg.append("%s (%s)" % (city.title(), len(toons[city])))
                if not content.startswith("!who matters") or city not in ERP_CITIES:
                    msg.append(", ".join(toons[city]))
                msg.append("")
                total += len(toons[city])
        msg.append("%i online." % total)
    elif content.startswith("!logosians") or content.startswith("!dragons"):
        toons = list_toons(min_level=80 if content.startswith("!l") else 100)
        total = 0
        for city in sorted(toons):
            msg.append("%s (%s)" % (city.title(), len(toons[city])))
            msg.append(", ".join(toons[city]))
            msg.append("")
            total += len(toons[city])
        msg.append("%i online." % total)
    elif content.startswith("!qw"):
        toons = list_toons(quick=True)
        msg.extend([", ".join(toons), "", "%i online." % len(toons)])
    elif content.startswith("!romaen") or content.startswith("!lettucepray"):
        romaen_list = get_romaen_list()
        romaen_set = set(romaen_list.get("contracts", ())) | set(
            romaen_list.get("rivals", ())
        )
        toons = set(list_toons(quick=True)) & romaen_set
        msg.extend([", ".join(toons), "", "%i online." % len(toons)])
    elif content.startswith("!namestats"):
        try:
            arg = content.split()[1]
        except IndexError:
            arg = None

        if arg not in ("online", "offline"):
            arg = "online"

        scaling_factor = 1
        if arg == "online":
            toons = list_toons(quick=True)
        else:
            scaling_factor = 3
            toons = [toon[1] for toon in show_toon_archive()]

        msg.extend(calculate_namestats(toons, scaling_factor=scaling_factor))

    if msg:
        if len(msg) == 1:
            await message.channel.send(msg[0])
        else:
            await message.channel.send("```\n%s\n```" % "\n".join(msg))


if __name__ == "__main__":
    client.run(os.environ["ACHAEA_WHOBOT_TOKEN"])
