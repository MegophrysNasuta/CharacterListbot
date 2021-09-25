#! /usr/bin/env python3
from collections import defaultdict
import json
from pprint import pprint
import sqlite3
import string
import sys

import requests


API_URL = 'http://api.achaea.com/characters'

API_FIELDS = (
    'name',
    'fullname',
    'city',
    'house',
    'level',
    'class',
    'mob_kills',
    'player_kills',
    'xp_rank',
    'explorer_rank',
)


class CharacterNotFound(KeyError):
    pass


def to_num(n):
    if n.endswith('k'):
        return int(n[:-1]) * 1000
    else:
        return int(n)


def get_toon_from_api(name):
    data = requests.get('%s/%s.json' % (API_URL, name)).json()
    if 'name' not in data:
        raise CharacterNotFound(name)
    return data


def setup_db_if_blank(db_connection):
    sql = "CREATE TABLE IF NOT EXISTS characters (id serial PRIMARY KEY, "
    cols = (('%s varchar(255) NOT NULL' % field) for field in API_FIELDS)
    sql += ', '.join(cols) + ');'
    db_connection.cursor().execute(sql)


def update_toon(db_connection, name):
    cursor = db_connection.cursor()
    data = get_toon_from_api(name)
    cursor.execute('UPDATE characters AS c SET %s WHERE c.name==:name' % (
                        ','.join(('%s=%s' % (field, ':%s' % field)
                                          for field in API_FIELDS))
                    ), data)
    return data


def get_or_create_toon(db_connection, name):
    cursor = db_connection.cursor()
    cursor.execute('SELECT c.city FROM characters c WHERE c.name == ?;',
                   (name,))
    try:
        return {'city': cursor.fetchall()[0][0]}
    except IndexError:
        data = get_toon_from_api(name)
        cursor.execute('INSERT INTO characters (%s) VALUES (%s)' %
                       (', '.join(API_FIELDS),
                        ', '.join((':%s' % field) for field in API_FIELDS)),
                       data)
        return data


def list_toons(update=False, quick=False):
    toon_list = {}
    data = requests.get('%s.json' % API_URL).json()
    toons = data['characters']
    if quick:
        return [toon['name'] for toon in toons]

    with sqlite3.connect('toons.db') as conn:
        setup_db_if_blank(conn)
        db_action = update_toon if update else get_or_create_toon
        for toon in toons:
            data = db_action(conn, toon['name'])
            toon_list.setdefault(data['city'], []).append(toon['name'])

    return toon_list


def show_game_feed():
    url = '%s.json' % API_URL.replace('characters', 'gamefeed')
    data = requests.get(url).json()
    return [row for row in data if row['type'] in ('DEA', 'DUE')]


def show_toon_archive():
    with sqlite3.connect('toons.db') as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM characters')
        return cursor.fetchall()


def search_toon_archive(name):
    with sqlite3.connect('toons.db') as conn:
        setup_db_if_blank(conn)
        return get_or_create_toon(conn, name)


if __name__ == '__main__':
    try:
        arg = sys.argv[1]
    except IndexError:
        # list all online
        toons = list_toons()
        total = 0
        for city in toons:
            print('%s (%s)' % (city.title(), len(toons[city])))
            print(', '.join(toons[city]))
            print()
            total += len(toons[city])
        print('%i online.' % total)
    else:
        if arg.lower() in ('ashtan', 'cyrene', 'eleusis',
                           'hashan', 'mhaldor', 'targossas'):
            city = arg.lower()
            toons = list_toons()
            print('%s (%s)' % (city.title(), len(toons[city])))
            print(', '.join(toons[city]))
        elif arg.lower() == 'update':
            toons = list_toons(update=True)
            toon_list = list_toons(quick=True)
            print('%i toons updated!' % len(toon_list))
        elif arg.lower() == 'offline':
            toon_archive = show_toon_archive()
            for toon in toon_archive:
                print(toon[1], end=', ')
            print('%i Achaeans known.' % len(toon_archive))
        elif arg.lower() == 'gamefeed':
            for death in show_game_feed():
                print(death['description'])
        elif arg.lower() == 'namestats':
            try:
                arg2 = sys.argv[2]
            except IndexError:
                arg2 = 'online'
            else:
                arg2 = arg2.lower()
                if arg2 not in ('online', 'offline'):
                    arg2 = 'online'

            if arg2 == 'online':
                toons = list(itertools.chain.from_iterable(list_toons().values()))
            else:
                toons = [toon[1] for toon in show_toon_archive()]

            namestats = defaultdict(int)
            for toon in toons:
                namestats[toon[0]] += 1

            for letter in string.ascii_uppercase:
                print('%s:' % letter, '#' * namestats[letter])
        else:
            try:
                data = search_toon_archive(arg)
            except CharacterNotFound as e:
                print('Character not found: %s' % e, file=sys.stderr)
            else:
                fullname = data.pop('fullname')
                print(fullname)
                print('=' * len(fullname))
                print('Level {level} {cls} in House {house} in {city}.'.format(
                        level=data.pop('level'),
                        cls=data.pop('class').title(),
                        house=data.pop('house').title(),
                        city=data.pop('city').title(),
                    ))
                name = data.pop('name')
                print('{name} has killed {d:,d} denizens and {a:,d} adventurers.'.format(
                        name=name,
                        d=to_num(data.pop('mob_kills')),
                        a=to_num(data.pop('player_kills')),
                    ))
                print('{name} is Explorer Rank {e:,d} and XP Rank {x:,d}.'.format(
                        name=name,
                        e=int(data.pop('explorer_rank')),
                        x=int(data.pop('xp_rank')),
                    ))
                if data:
                    pprint(data)
