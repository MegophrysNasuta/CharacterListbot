#! /usr/bin/env python3
from collections import defaultdict
from datetime import datetime
import json
from pprint import pprint
import sqlite3
import string
import sys

from dateutil.parser import parse as parse_date
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
    sql = """
    CREATE TABLE IF NOT EXISTS deaths (id serial PRIMARY_KEY,
                                       killer varchar(255) NOT NULL,
                                       corpse varchar(255) NOT NULL,
                                       external_id varchar(255) NOT NULL,
                                       timestamp datetime DEFAULT CURRENT_TIMESTAMP);
    """
    db_connection.cursor().execute(sql)
    sql = """
    CREATE TABLE IF NOT EXISTS updates (id serial PRIMARY_KEY,
                                        timestamp datetime DEFAULT CURRENT_TIMESTAMP)
    """
    db_connection.cursor().execute(sql)


def check_for_updates(since):
    with sqlite3.connect('toons.db') as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(timestamp) FROM updates LIMIT 1')

        do_update = False
        try:
            ts = cursor.fetchall()[0][0]
        except IndexError:
            do_update = True
        else:
            if not ts:
                do_update = True
            else:
                dt = parse_date(ts)
                do_update = (abs(datetime.utcnow() - dt).total_seconds() >
                             int(since))

        if do_update:
            cursor.execute('INSERT INTO updates')
        return do_update

def update_toon(db_connection, name):
    cursor = db_connection.cursor()
    data = get_toon_from_api(name)
    cursor.execute('UPDATE characters AS c SET %s WHERE c.name==:name' % (
                        ','.join(('%s=%s' % (field, ':%s' % field)
                                          for field in API_FIELDS))
                    ), data)
    return data


def get_or_create_deathsight(db_connection, killer, corpse, external_id):
    cursor = db_connection.cursor()
    cursor.execute('SELECT d.killer, d.corpse FROM deaths d WHERE d.external_id == ?;',
                   (external_id,))
    try:
        killer, corpse = cursor.fetchall()[0]
    except (IndexError, ValueError):
        cursor.execute('INSERT INTO deaths (killer, corpse, external_id) VALUES (?, ?, ?)',
                       (killer, corpse, external_id))
        return True
    else:
        return False


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


def show_death_history():
    with sqlite3.connect('toons.db') as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        cursor.execute('SELECT killer, corpse from deaths')
        return cursor.fetchall()


def show_kdr(player, against=None):
    with sqlite3.connect('toons.db') as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        sql = 'SELECT count(corpse) FROM deaths WHERE killer == ?'
        args = [player.title()]
        if against:
            sql += ' AND corpse == ?'
            args.append(against.title())
        cursor.execute(sql, args)
        try:
            kills = cursor.fetchall()[0][0]
        except IndexError:
            kills = 0

        sql = 'SELECT count(killer) FROM deaths WHERE corpse == ?'
        if against:
            sql += ' AND killer == ?'
        cursor.execute(sql, args)
        try:
            deaths = cursor.fetchall()[0][0]
        except IndexError:
            deaths = 0

        return kills, deaths

def show_game_feed(types=('DEA', 'DUE'), update=False):
    url = '%s.json' % API_URL.replace('characters', 'gamefeed')
    data = requests.get(url).json()
    feed = [row for row in data if row['type'] in types]
    if not update:
        return feed
    else:
        deaths_added = 0
        for death in feed:
            try:
                corpse, killer = death['description'].split(' was slain by ')
            except ValueError:
                killer, corpse = death['description'].split(' defeated ')
                killer = killer.strip()
                corpse = corpse.split(None, 1)[0]
            else:
                killer = killer.strip().rstrip('.')
                corpse = corpse.strip()

            with sqlite3.connect('toons.db') as conn:
                setup_db_if_blank(conn)
                if get_or_create_deathsight(conn, external_id=str(death['id']),
                                            killer=killer, corpse=corpse):
                    deaths_added += 1
        return deaths_added


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
        if arg.lower() == 'hi':
            print('Hello, you')
        elif arg.lower() in ('ashtan', 'cyrene', 'eleusis',
                           'hashan', 'mhaldor', 'targossas'):
            city = arg.lower()
            toons = list_toons()
            print('%s (%s)' % (city.title(), len(toons[city])))
            print(', '.join(toons[city]))
        elif arg.lower() == 'update':
            toons = list_toons(update=True)
            print('%i toons updated!' % len(toons))
            deaths_added = show_game_feed(update=True)
            print('%i deaths added!' % deaths_added)
        elif arg.lower() == 'offline':
            toon_archive = show_toon_archive()
            for toon in toon_archive:
                print(toon[1], end=', ')
            print('%i Achaeans known.' % len(toon_archive))
        elif arg.lower() == 'deathhistory':
            for death in show_death_history():
                print('%s killed %s.' % death[:2])
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
