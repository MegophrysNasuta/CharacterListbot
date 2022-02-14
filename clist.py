#! /usr/bin/env python3
from collections import defaultdict
from datetime import date, datetime, timedelta
import itertools
import json
from os import environ as env
from pprint import pprint
import string
import sys

from dateutil.parser import parse as parse_date
import requests

from db import DBContextManager


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

DB_TYPE = 'postgres' if 'DATABASE_URL' in env else 'sqlite'


class CharacterNotFound(KeyError):
    pass


def expand_kills(n):
    if n.endswith('k'):
        return 'over {:,d}'.format(int(n[:-1]) * 1000)
    else:
        return '{:,d}'.format(int(n))


def fmt_sql(sql, n):
    if DB_TYPE == 'sqlite':
        return sql % tuple('?' for _ in range(n))
    return sql


def get_toon_from_api(name):
    data = requests.get('%s/%s.json' % (API_URL, name)).json()
    if 'name' not in data:
        raise CharacterNotFound(name)
    return data


def setup_db_if_blank(db_connection):
    db = {
        'postgres': {
            'pk': 'serial PRIMARY KEY',
            'bool': 'smallint DEFAULT 0',
            'text': 'varchar(255) NOT NULL',
            'date': 'timestamp DEFAULT CURRENT_TIMESTAMP',
            'int': 'int',
        },
        'sqlite': {
            'pk': 'integer PRIMARY KEY',
            'bool': 'integer DEFAULT 0',
            'text': 'text NOT NULL',
            'date': 'text DEFAULT CURRENT_TIMESTAMP',
            'int': 'integer',
        },
    }

    sql = "CREATE TABLE IF NOT EXISTS characters (id %s, "
    sql %= db[DB_TYPE]['pk']

    cols = (('%s %s' % (field, db[DB_TYPE]['text'])) for field in API_FIELDS)
    sql += ', '.join(cols) + ');'
    db_connection.cursor().execute(sql)

    sql = """
    CREATE TABLE IF NOT EXISTS deaths (id %(pk)s,
                                       killer %(text)s,
                                       corpse %(text)s,
                                       external_id %(text)s,
                                       kdr_count %(bool)s,
                                       timestamp %(date)s);
    """ % db[DB_TYPE]
    db_connection.cursor().execute(sql)
    sql = """
    CREATE TABLE IF NOT EXISTS kdr (id %(pk)s,
                                    timestamp %(date)s,
                                    kills %(int)s,
                                    deaths %(int)s,
                                    kdr %(text)s);
    """ % db[DB_TYPE]
    db_connection.cursor().execute(sql)
    sql = """
    CREATE TABLE IF NOT EXISTS updates (id %(pk)s,
                                        timestamp %(date)s);
    """ % db[DB_TYPE]
    db_connection.cursor().execute(sql)
    sql = """
    CREATE TABLE IF NOT EXISTS polls (id %(pk)s,
                                      question %(text)s,
                                      owner %(text)s,
                                      locked %(bool)s,
                                      message_id %(text)s);
    """ % db[DB_TYPE]
    db_connection.cursor().execute(sql)
    sql = """
    CREATE TABLE IF NOT EXISTS pollopts (id %(pk)s,
                                         poll %(int)s%(inline_fk)s,
                                         emoji %(text)s,
                                         meaning %(text)s,
                                         owner %(text)s,
                                         votes %(int)s,
                                         UNIQUE (poll, emoji, meaning)%(outro_fk)s);
    """
    arg = db[DB_TYPE]
    arg['inline_fk'] = ' REFERENCES polls(id)' if DB_TYPE == 'postgres' else ''
    arg['outro_fk'] = ',\nFOREIGN KEY(poll) REFERENCES polls(id)' if DB_TYPE == 'sqlite' else ''
    db_connection.cursor().execute(sql % arg)


def adjust_pollopt_vote(emoji, vote_count):
    with DBContextManager() as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        emoji = str(emoji) if emoji.is_unicode_emoji() else str(emoji.id)
        print('%s now has %i votes.' % (emoji, vote_count))
        sql = "UPDATE pollopts SET votes = %s WHERE emoji = %s"
        cursor.execute(sql, (int(vote_count), emoji))


def calculate_namestats(toons, scaling_factor=1):
    returned_msg = []
    if scaling_factor > 1:
        returned_msg.append('# ~ %i adventurers' % scaling_factor)

    namestats = defaultdict(int)
    for toon in toons:
        namestats[toon[0]] += 1

    backwards_alpha = list(reversed(string.ascii_uppercase))
    def sort_func(key):
        return namestats[key], backwards_alpha.index(key)

    for letter in reversed(sorted(namestats, key=sort_func)):
        number = int(namestats[letter] / int(scaling_factor))
        returned_msg.append('%s: %s' % (letter, '#' * number))

    for letter in string.ascii_uppercase:
        if letter not in namestats:
            returned_msg.append('%s:' % letter)

    return returned_msg


def check_for_updates(since):
    with DBContextManager() as conn:
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
                if not isinstance(ts, datetime):
                    ts = parse_date(ts)
                do_update = (abs(datetime.utcnow() - ts).total_seconds() >
                             int(since))

        if do_update:
            cursor.execute('INSERT INTO updates (timestamp) VALUES (CURRENT_TIMESTAMP)')
        return do_update


def create_poll(question, owner, message_id, locked=False):
    with DBContextManager() as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        sql = ("INSERT INTO polls (question, owner, message_id, locked) "
               "VALUES (%s, %s, %s, %s) RETURNING id")
        cursor.execute(sql, (question, owner, message_id, int(bool(locked))))
        return cursor.fetchone()[0]


def create_pollopt(poll_id, emoji, meaning, owner, add_vote=False):
    with DBContextManager() as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        sql = ("INSERT INTO pollopts (poll, emoji, meaning, owner, votes) "
               "VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING "
               "RETURNING id, poll")
        emoji = str(emoji) if emoji.is_unicode_emoji() else str(emoji.id)
        cursor.execute(sql, (poll_id, emoji, meaning, owner, int(bool(add_vote))))
        return cursor.fetchone()


def get_or_create_deathsight(db_connection, killer, corpse, external_id,
                             counts_for_kdr=False):
    cursor = db_connection.cursor()
    cursor.execute(fmt_sql('SELECT d.killer, d.corpse FROM deaths d '
                           "WHERE d.external_id = %s;", 1), (external_id,))
    try:
        killer, corpse = cursor.fetchall()[0]
    except (IndexError, ValueError):
        cursor.execute(fmt_sql('INSERT INTO deaths (killer, corpse, external_id, kdr_count) '
                               "VALUES (%s, %s, %s, %s)", 4),
                       (killer, corpse, external_id, int(counts_for_kdr)))
        return True
    else:
        return False


def get_or_create_toon(db_connection, name):
    cursor = db_connection.cursor()
    sql = fmt_sql(("SELECT c.city, c.level FROM characters c "
                   "WHERE c.name = %s ORDER BY c.id DESC;"), 1)
    cursor.execute(sql, (name,))
    data = None
    try:
        row = cursor.fetchall()[0]
        data = {'city': row[0], 'level': row[1]}
    except IndexError:
        data = get_toon_from_api(name)
        cursor.execute(fmt_sql("INSERT INTO characters (%s) VALUES (%s)" % (
                               ', '.join(API_FIELDS),
                               ', '.join('%s' for field in API_FIELDS)),
                               len(API_FIELDS)),
                       [data[field] for field in API_FIELDS])
    return data


def get_poll_owner(poll_id):
    with DBContextManager() as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        cursor.execute('SELECT owner FROM polls WHERE id = %s', (poll_id,))
        return cursor.fetchone()[0]


def get_poll_report(poll_id, message):
    with DBContextManager() as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        cursor.execute('SELECT message_id, question, owner FROM polls WHERE id = %s', (poll_id,))
        result = cursor.fetchone()
        if result is None:
            return ('Poll %i not found.' % poll_id,)
        message_id, question, owner = result
        report_msg = ['Poll %i posted by <@%s>' % (poll_id, owner),
                      '> %s' % question.title().replace("'S", "'s"), '']
        sql = ('SELECT emoji, meaning, votes FROM pollopts '
               'WHERE poll = %s ORDER BY votes, meaning DESC')
        cursor.execute(sql, (poll_id,))
        for emoji, meaning, votes in cursor.fetchall():
            report_msg.append('%s (%s):\n\t%s' % (emoji, meaning, '#' * int(votes)))
        return report_msg


def is_poll_locked(poll_id):
    with DBContextManager() as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        cursor.execute('SELECT locked FROM polls WHERE id = %s', (poll_id,))
        return bool(cursor.fetchone()[0])


def list_toons(update=False, quick=False, min_level=1):
    toon_list = {}
    data = requests.get('%s.json' % API_URL).json()
    toons = data['characters']
    if quick:
        return [toon['name'] for toon in toons]

    with DBContextManager() as conn:
        setup_db_if_blank(conn)
        db_action = update_toon if update else get_or_create_toon
        for toon in toons:
            data = db_action(conn, toon['name'])
            if int(data['level']) >= min_level:
                toon_list.setdefault(data['city'], []).append(toon['name'])

    return toon_list


def set_pollopt_meaning(pollopt_id, meaning, requester_id):
    with DBContextManager() as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        cursor.execute(('UPDATE pollopts SET meaning = %s '
                        'WHERE id = %s AND owner = %s '
                        'RETURNING id'),
                       (meaning, pollopt_id, str(requester_id)))
        return cursor.fetchone()


def show_death_history(corpse=None, killer=None):
    with DBContextManager() as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        if corpse:
            cursor.execute(fmt_sql('SELECT MIN(timestamp) FROM deaths '
                                   "WHERE corpse = %s;", 1), (corpse,))
            try:
                min_ts = cursor.fetchall()[0][0]
            except IndexError:
                return
            cursor.execute(fmt_sql('SELECT killer, COUNT(killer) AS count FROM deaths '
                                   "WHERE corpse = %s GROUP BY killer HAVING deaths.count > 0 ORDER BY count DESC LIMIT 40", 1),
                           (corpse,))
            return {'since': min_ts, 'deaths': cursor.fetchall()}
        elif killer:
            cursor.execute(fmt_sql('SELECT MIN(timestamp) FROM deaths '
                                   "WHERE lower(killer) = %s;", 1),
                           (killer.lower(),))
            try:
                min_ts = cursor.fetchall()[0][0]
            except IndexError:
                return
            cursor.execute(fmt_sql("SELECT corpse, COUNT(corpse) AS count FROM deaths "
                                   "WHERE lower(killer) = %s GROUP BY corpse  HAVING deaths.count > 0"
                                   "ORDER BY count DESC LIMIT 40", 1),
                           (killer.lower(),))
            return {'since': min_ts, 'kills': cursor.fetchall()}
        else:
            cursor.execute('SELECT MIN(timestamp) FROM deaths')
            try:
                min_ts = cursor.fetchall()[0][0]
            except IndexError:
                return
            cursor.execute('SELECT killer, corpse FROM deaths')
            return {'since': min_ts, 'deaths': cursor.fetchall()}


def expunge_old_data():
    with DBContextManager() as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM characters AS c "
                       "WHERE EXISTS (SELECT c_.name FROM characters AS c_ "
                       "              WHERE c_.name = c.name AND "
                       "              c_.id <> c.id);")
        nine_days_ago = (date.today() - timedelta(days=9)).isoformat()
        cursor.execute("DELETE FROM deaths AS d "
                       "WHERE d.timestamp < '%s'" % nine_days_ago)


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

            counts_for_kdr = (death['type'] == 'DEA' and
                              ' ' not in killer)
            if counts_for_kdr:
                try:
                    get_toon_from_api(killer)
                except CharacterNotFound:
                    counts_for_kdr = False

            with DBContextManager() as conn:
                setup_db_if_blank(conn)
                if get_or_create_deathsight(conn, external_id=str(death['id']),
                                            killer=killer, corpse=corpse,
                                            counts_for_kdr=counts_for_kdr):
                    deaths_added += 1

        expunge_old_data()
        return deaths_added


def recalculate_kdr():
    with DBContextManager() as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        sql = """
        INSERT INTO kdr (kills, deaths, kdr)
        SELECT CASE WHEN COUNT(d.corpse) = 0 THEN 1
               ELSE COUNT(d.corpse) END AS kills,
        (SELECT CASE WHEN COUNT(d2.killer) = 0 THEN 1
                ELSE COUNT(d2.killer) END
            FROM deaths d2
            WHERE d2.corpse = d.killer
            AND d2.kdr_count = 1) AS deaths,
        -1 AS kdr
            FROM deaths d
            WHERE d.kdr_count = 1
            GROUP BY d.killer;
        """
        cursor.execute(sql)
        cursor.execute("UPDATE kdr SET kdr = "
                       "CAST(kills AS DECIMAL) / deaths "
                       "WHERE kdr = -1;")


def show_kdr(player, against=None):
    with DBContextManager() as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        sql = "SELECT count(corpse) FROM deaths WHERE kdr_count = 1 AND killer = %s"
        args = [player.title()]
        if against:
            sql += " AND corpse = %s"
            args.append(against.title())
        cursor.execute(fmt_sql(sql, len(args)), args)
        try:
            kills = cursor.fetchall()[0][0]
        except IndexError:
            kills = 0

        sql = "SELECT count(killer) FROM deaths WHERE kdr_count = 1 AND corpse = %s"
        if against:
            sql += " AND killer = %s"
        cursor.execute(fmt_sql(sql, len(args)), args)
        try:
            deaths = cursor.fetchall()[0][0]
        except IndexError:
            deaths = 0

        return kills, deaths


def search_toon_archive(name):
    with DBContextManager() as conn:
        setup_db_if_blank(conn)
        return get_or_create_toon(conn, name)


def show_toon_archive():
    with DBContextManager() as conn:
        setup_db_if_blank(conn)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM characters')
        return cursor.fetchall()


def update_toon(db_connection, name):
    cursor = db_connection.cursor()
    data = get_toon_from_api(name)
    args = [name] + [data[field] for field in API_FIELDS]
    sql = "UPDATE characters SET %s WHERE name = %%s" % (
              ', '.join(("%s=%%s" % field
                        for field in API_FIELDS)),)
    sql = fmt_sql(sql, len(args))
    cursor.execute(sql, args)
    return data


if __name__ == '__main__':
    try:
        arg = sys.argv[1]
    except IndexError:
        # list all online
        toons = list_toons()
        total = 0
        for city in sorted(toons):
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
            print('Toons updated!')
            deaths_added = show_game_feed(update=True)
            print('%i deaths added!' % deaths_added)
        elif arg.lower() == 'offline':
            toon_archive = show_toon_archive()
            for toon in toon_archive:
                print(toon[1], end=', ')
            print('%i Achaeans known.' % len(toon_archive))
        elif arg.lower() == 'deathhistory':
            death = None
            data = show_death_history()
            for death in data['deaths']:
                print('%s killed %s.' % death[:2])
            if death:
                print('(records since %s)' % data['since'])
            else:
                print('No records found!')
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

            print('\n'.join(calculate_namestats(toons)))
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
                print('{name} has killed {d} denizens and {a} adventurers.'.format(
                        name=name,
                        d=expand_kills(data.pop('mob_kills')),
                        a=expand_kills(data.pop('player_kills')),
                    ))
                print('{name} is Explorer Rank {e:,d} and XP Rank {x:,d}.'.format(
                        name=name,
                        e=int(data.pop('explorer_rank')),
                        x=int(data.pop('xp_rank')),
                    ))
                if data:
                    pprint(data)
