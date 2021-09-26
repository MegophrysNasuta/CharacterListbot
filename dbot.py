#!/usr/bin/env python
import ast
from collections import defaultdict
import operator as op
import os
import random
import string
import sys

import discord

from clist import (CharacterNotFound, check_for_updates,
                   list_toons, show_game_feed, show_kdr,
                   show_toon_archive, search_toon_archive, to_num)


client = discord.Client()


math_operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
                  ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
                  ast.USub: op.neg}


def eval_(node):
    if isinstance(node, ast.Num): # <number>
        return node.n
    elif isinstance(node, ast.BinOp): # <left> <operator> <right>
        return math_operators[type(node.op)](eval_(node.left), eval_(node.right))
    elif isinstance(node, ast.UnaryOp): # <operator> <operand> e.g., -1
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
    return eval_(ast.parse(expr, mode='eval').body)


@client.event
async def on_ready():
    print('Ready!')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    msg = []
    content = message.content.lower()
    if content.startswith('!honours'):
        taunt_the_uk = (
            'TEAM AMERICA, F**K YEAH! :flag_us::flag_us::flag_us:',
            'Is this Romaen??',
            "IT'S HONORS, BABY!! WOOOOO!!!! *\*fires machine gun into air\**",
            "I don't have to listen to this British crap.",
            "Rejoin the EU, already. What are y'all doing over there?",
            """
:flag_gb:                    :flag_gb:           :flag_gb: :flag_gb:
:flag_gb::flag_gb:       :flag_gb:       :flag_gb:          :flag_gb:
:flag_gb:      :flag_gb: :flag_gb:       :flag_gb:          :flag_gb:
:flag_gb:                    :flag_gb:           :flag_gb: :flag_gb:
            """,
            "https://media.giphy.com/media/j0GW2I35KnU5e5BT7L/giphy.gif?cid=ecf05e47vnq3lhoqsc1ut9x06y1tvnqh07yi3qfesdxenz5k&rid=giphy.gif&ct=g",
            "https://media.giphy.com/media/ZdxLZAMhQcaKbIGdug/giphy.gif?cid=ecf05e47dyuhhicefn0p2nak6v5dtia4i73jovj93sbnjp0g&rid=giphy.gif&ct=g",
            "https://media.giphy.com/media/NaA840F7VJSHS/giphy.gif?cid=ecf05e47h7sot76tf80g7mss1pj5ru8bpywo8rfr0ltxdc20&rid=giphy.gif&ct=g",
            "https://media.giphy.com/media/deSTGRBAr6TdkVEjCd/giphy.gif?cid=ecf05e478zcb8s57d8lxbjhm3pje0ixh0tmcr1sr2eet35mj&rid=giphy.gif&ct=g",
        )
        msg.append(random.choice(taunt_the_uk))
    elif content.startswith('!pet cossi'):
        msg.append('*rubs up against <@%s>\'s leg*' % message.author.id)
    elif content.startswith('!math'):
        try:
            expr = content.split(None, 1)[1]
        except IndexError:
            msg.append('**MATH!!**')
        else:
            try:
                msg.append(eval_expr(expr))
            except ZeroDivisionError:
                msg.append('Ow. What just happened?')
            except (SyntaxError, TypeError):
                msg.append('Think of me like a small Casio. I think you need a TI-92 for that one.')
    elif (content.startswith('!whois') or
            content.startswith('!honors')):
        try:
            name = content.split(None, 1)[1]
        except IndexError:
            if content.startswith('!honors'):
                msg.append('Honors whom?!')
            else:
                msg.append('Who is what, man?!')
        except Exception as e:
            print('Error: ', str(e), file=sys.stderr)
            raise
        else:
            try:
                data = search_toon_archive(name)
            except CharacterNotFound:
                msg.append('"%s" is not real. You made that up.' % name.title())
            else:
                fullname = data.pop('fullname')
                msg.extend([fullname, '=' * len(fullname)])
                msg.append(
                    'Level {level} {cls} in House {house} in {city}.'.format(
                        level=data.pop('level'),
                        cls=data.pop('class').title(),
                        house=data.pop('house').title(),
                        city=data.pop('city').title(),
                    )
                )
                msg.append(
                    ('{name} has killed {d:,d} denizens and '
                     '{a:,d} adventurers.').format(
                        name=name.title(),
                        d=to_num(data.pop('mob_kills')),
                        a=to_num(data.pop('player_kills')),
                    )
                )
                msg.append(
                    '{name} is Explorer Rank {e:,d} and XP Rank {x:,d}.'.format(
                        name=name.title(),
                        e=int(data.pop('explorer_rank')),
                        x=int(data.pop('xp_rank')),
                    )
                )
    elif content.startswith('!death'):
        msg.extend([death['description'] for death in show_game_feed()])
    elif content.startswith('!kdr'):
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
                if ' ' not in against:
                    against = against.title()
                msg.append('No records for %s vs %s.' % (player.title(), against))
            else:
                msg.append('No records for %s.' % player.title())
        else:
            if kills and not deaths:
                if against:
                    rpt_line = '%s is on a perfect %i-kill streak against %s!'
                    rpt_line %= (player.title(), kills, against.title())
                else:
                    rpt_line = '%s is on a perfect %i-kill streak!'
                    rpt_line %= (player.title(), kills)
            else:
                kdr = '%i%%' % ((kills / deaths) * 100)
                if against:
                    if ' ' not in against:
                        against = against.title()
                    rpt_line = '%s has killed %s %i times and died %i times. KDR: %s'
                    rpt_line %= (player.title(), against, kills, deaths, kdr)
                else:
                    rpt_line = '%s has killed %i times and died %i times. KDR: %s'
                    rpt_line %= (player.title(), kills, deaths, kdr)

            msg.append(rpt_line)
    elif content.startswith('!who') or content.startswith('!online'):
        toons = list_toons()
        total = 0
        for city in sorted(toons):
            msg.append('%s (%s)' % (city.title(), len(toons[city])))
            msg.append(', '.join(toons[city]))
            msg.append('')
            total += len(toons[city])
        msg.append('%i online.' % total)
    elif content.startswith('!qw'):
        toons = list_toons(quick=True)
        msg.extend([', '.join(toons), '', '%i online.' % len(toons)])
    elif content.startswith('!namestats'):
        try:
            arg = content.split()[1]
        except IndexError:
            arg = None

        if arg not in ('online', 'offline'):
            arg = 'online'

        if arg == 'online':
            toons = list_toons(quick=True)
        else:
            toons = [toon[1] for toon in show_toon_archive()]

        namestats = defaultdict(int)
        for toon in toons:
            namestats[toon[0]] += 1

        for letter in string.ascii_uppercase:
            msg.append('%s: %s' % (letter, '#' * namestats[letter]))

    if msg:
        if len(msg) == 1:
            await message.channel.send(msg[0])
        else:
            await message.channel.send('```%s```' % '\n'.join(msg))

    if check_for_updates(300):
        list_toons(update=True)
        deaths_added = show_game_feed(update=True)
        print('Toons updated; %i deaths added.' % deaths_added)


if __name__ == '__main__':
    client.run(os.environ['ACHAEA_WHOBOT_TOKEN'])
