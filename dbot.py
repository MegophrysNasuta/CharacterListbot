#!/usr/bin/env python
from collections import defaultdict
import itertools
import os
import string
import sys

import discord

from clist import (CharacterNotFound, list_toons, show_toon_archive,
                   search_toon_archive, to_num)


client = discord.Client()


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
        msg.append('TEAM AMERICA, F**K YEAH! (Spell it right, Romaen)')
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
                msg.append('"%s" is not real. You made that up.' % name)
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
                        name=name,
                        d=to_num(data.pop('mob_kills')),
                        a=to_num(data.pop('player_kills')),
                    )
                )
                msg.append(
                    '{name} is Explorer Rank {e:,d} and XP Rank {x:,d}.'.format(
                        name=name,
                        e=int(data.pop('explorer_rank')),
                        x=int(data.pop('xp_rank')),
                    )
                )
    elif (content.startswith('!who') or content.startswith('!qw') or
          content.startswith('!qwho') or content.startswith('!online')):
        toons = list_toons()
        total = 0
        for city in toons:
            msg.append('%s (%s)' % (city.title(), len(toons[city])))
            msg.append(', '.join(toons[city]))
            msg.append('')
            total += len(toons[city])
        msg.append('%i online.' % total)
    elif content.startswith('!namestats'):
        try:
            arg = content.split()[1]
        except IndexError:
            arg = None

        if arg not in ('online', 'offline'):
            arg = 'online'

        if arg == 'online':
            toons = list(itertools.chain.from_iterable(list_toons().values()))
        else:
            toons = [toon[1] for toon in show_toon_archive()]

        namestats = defaultdict(int)
        for toon in toons:
            namestats[toon[0]] += 1

        for letter in string.ascii_uppercase:
            msg.append('%s: %s' % (letter, '#' * namestats[letter]))

    if msg:
        await message.channel.send('```%s```' % '\n'.join(msg))


if __name__ == '__main__':
    client.run(os.environ['ACHAEA_WHOBOT_TOKEN'])
