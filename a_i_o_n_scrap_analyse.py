import re
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from queue import Queue
from random import choice
from time import sleep
from typing import Optional

import matplotlib
import numpy as np
import requests
from bs4 import BeautifulSoup
from matplotlib.ticker import MultipleLocator
from pandas import DataFrame
from peewee import Case, CharField, CompositeKey, DateTimeField, FloatField, fn, ForeignKeyField, Model, ModelSelect, OperationalError, PostgresqlDatabase, PrimaryKeyField
from psycopg2 import connect
from requests import Response

from util import fill_rows, now, query_to_df, run

# config #
boss_filter_on = True
# boss_filter_on = False
# blacklist_bosses = None
blacklist_bosses = ["Generator", "Spaller"]
blacklist_exact_bosses = None
# bosses_exact_blacklist = ("Main Power Generator in Dark Poeta 1.9",)
# db_name = "db"  # db_name must be on lower case for a dynamic creation

# init #
healers = ("Chanter", "Cleric", "Templar")
all_classes = ("Assassin", "Ranger", "Spiritmaster", "Sorcerer", "Chanter", "Cleric", "Gladiator", "Templar", "Executor")
allowed_servers = ("Atreia", "Tahabata")
INDEX_ERROR_COUNT = 0
LOCKER_CONSUME = 0
consume_lock = threading.Lock()
url_api = "".join(["m", "y", "a", "i", "o", "n", ".", "e", "u"])
db_name = "".join(["a", "i", "o", "n"])
# db_name = [char for char in url_api.split() if "." not in char]
user = "postgres"
password = "ale"
# Install Postgresql
try:
    db = PostgresqlDatabase(db_name, user=user, password=password)
    db.connect()
except OperationalError:
    connection = connect(user=user, password=password, host="localhost", port="5432")
    connection.autocommit = True
    db_cursor = connection.cursor()
    db_cursor.execute(f"CREATE DATABASE {db_name};")
    db_cursor.close()
    connection.close()
    db = PostgresqlDatabase(db_name, user=user, password=password)
    db.connect()


class Boss(Model):
    num = PrimaryKeyField()
    name = CharField()
    server = CharField()
    faction = CharField()
    start = DateTimeField()
    minutes = FloatField()

    class Meta:
        database = db
        table_name = "boss"


class PlayerFight(Model):
    name = CharField()
    server = CharField()  # not redundant
    faction = CharField()  # not redundant
    class_ = CharField(column_name="class")
    dps = FloatField()
    hps = FloatField()
    boss_num = ForeignKeyField(Boss, backref="players")

    class Meta:
        database = db
        table_name = "player_fight"
        primary_key = CompositeKey("name", "server", "boss_num")


def scrap_n_update_db(start_index=4000000):
    """ Parse/gather data from 'url_api' and insert the data in a database at the same time
    Beautifulsoup functions must be updated if the website elements position change
    """
    global INDEX_ERROR_COUNT

    def get_response_page(i) -> Response:
        url = f"https://{url_api}/PvESession/{i}"
        try:
            response = requests.get(url)
            if response is None:
                raise ValueError("Response is None")
            return response
        except (requests.RequestException, ValueError):
            print("retry", url)
            sleep(30)
            return get_response_page(i)

    def scrap_page_n_update_db(index, page_response) -> None:
        def get_boss_time() -> tuple[datetime, datetime]:
            session = soup.find("h6").next
            boss_date = session[len("Session: "):]
            pattern = r"(\d{2}\.\d{2}\.\d{4}) (\d{2}:\d{2}:\d{2}) - (\d{2}:\d{2}:\d{2})"
            date, start, end = re.match(pattern, boss_date).groups()
            format_ = "%d.%m.%Y %H:%M:%S"
            boss_start, boss_end = datetime.strptime(date + " " + start, format_), datetime.strptime(date + " " + end, format_)
            if boss_end < boss_start:
                boss_end += timedelta(days=1)
            return boss_start, boss_end

        def fill_boss_db(i) -> float:
            boss_start, boss_end = get_boss_time()
            boss_minutes = round((boss_end - boss_start).total_seconds() / 60, 2)
            version_string = soup.find("h6").find_next_sibling(lambda tag: tag.name == "h6" and "Version" in tag.text).text
            version = re.match(r".*: (?P<version>\d+.?\d*)", version_string).groups()[0]
            boss_name = soup.find("h2").text.strip() + " " + version
            player1_faction = "Elyos" if "Elyos" in soup.find_all("tr")[1].find_all("img")[0]["src"] else "Asmodian"
            fill_rows(Boss, ["num", "name", "server", "faction", "start", "minutes"],
                      [i, boss_name, player1_server, player1_faction, boss_start, boss_minutes])
            return boss_minutes

        def find_index_field() -> tuple[int, int, int, int, int]:
            headers = soup.find_all("th")
            server_tr, player_tr, dps_tr, heal_tr, dmg_tr = [None] * 5
            for j in range(1, len(headers)):
                if "player" in headers[j].text.lower():
                    player_tr = j - 1
                elif "server" in headers[j].text.lower():
                    server_tr = j - 1
                elif "dps" == headers[j].text.lower() or "alldps" == headers[j].text.lower():
                    dps_tr = j - 1
                elif "dmg" == headers[j].text.lower() or "alldmg" == headers[j].text.lower():
                    dmg_tr = j - 1
                elif "heal" in headers[j].text.lower():
                    heal_tr = j - 1
            assert all(map(lambda x: x is not None, [server_tr, player_tr, dps_tr, heal_tr]))
            return server_tr, player_tr, dps_tr, heal_tr, dmg_tr

        def fill_player_db(i, tr, server_tr, player_tr, heal_tr, dmg_tr) -> Optional[str]:
            player_data = tr.find_all("td")
            player_name = player_data[player_tr].text.strip()
            player_faction = "Elyos" if "Elyos" in player_data[0].find_all("img")[0]["src"] else "Asmodian"
            player_class = Path(player_data[0].find_all("img")[1]["src"]).stem
            player_server = player_data[server_tr].text.strip()
            player_dmg = float(player_data[dmg_tr].text.strip().replace(",", "").replace(".", ""))
            player_heal = float(player_data[heal_tr].text.strip().replace(",", "").replace(".", ""))
            player_dps = int(player_dmg / seconds)
            player_hps = int(player_heal / seconds)
            # TODO for asian servers, servers allow duplicate (name, server, boss_num) : replace to (id_char, server, boss_num)
            if not PlayerFight.select().where((PlayerFight.name == player_name) &
                                              (PlayerFight.server == player_server) &
                                              (PlayerFight.boss_num == i)).exists():
                fill_rows(PlayerFight, ["name", "server", "faction", "class_", "dps", "hps", "boss_num"],
                          [player_name, player_server, player_faction, player_class, player_dps, player_hps, i])
            else:
                return "duplicate"

        def fill_players_db(i) -> None:
            server_tr, player_tr, _, heal_tr, dmg_tr = find_index_field()
            rows_player = soup.find_all("tr")[1:-1]
            for tr in rows_player:
                if fill_player_db(i, tr, server_tr, player_tr, heal_tr, dmg_tr) == "duplicate":
                    PlayerFight.delete().where(PlayerFight.boss_num == i).execute()
                    return

        global INDEX_ERROR_COUNT, LOCKER_CONSUME
        soup = BeautifulSoup(page_response.text, "html.parser")
        try:
            player1_server = soup.find_all("tr")[1].find_all("td")[1].text.strip()
            INDEX_ERROR_COUNT = 0
        except IndexError:
            INDEX_ERROR_COUNT += 1
            print_safe[index] += f"IndexError {INDEX_ERROR_COUNT}"
            return
        player_names = [tr.find_all("td")[0].text.strip() for tr in soup.find_all("tr")[1:-1]]
        not_allowed_characters = ["▋"]
        if sum((char in player_name) for char in not_allowed_characters for player_name in player_names) >= 2:
            # ▋ Happens when my_a_i_o_n doesn't recognize some characters in the player name
            # This may result to a duplication name/class for a same Boss instance
            # The Boss instance and players within it are ignored when at least 2 player names contain ▋
            print_safe[index] += f"pass {player_names}"
            return
        minutes = fill_boss_db(index)
        seconds = minutes * 60 or 1
        fill_players_db(index)

    def db_insert_pvesession(index):
        response = get_response_page(index)
        # INDEX_ERROR_COUNT += bool(response.status_code == 404) manage just the 404 error, It doesn't encompass all errors
        print_safe[index] += "{} {} ".format(response.url, (response.status_code == 200) or response.status_code)
        scrap_page_n_update_db(index, response)

    def consume(tasks):
        """ Consume all tasks in parallel from the current queue and wait for each thread to complete """
        global LOCKER_CONSUME
        while True:
            with consume_lock:
                if not LOCKER_CONSUME:
                    break
        sleep(0.01)
        LOCKER_CONSUME = True
        threads = []
        size = len(tasks.queue)
        while len(threads) < size:
            task = tasks.get()
            threads.append(run(task, name="task"))
        for thread in threads:
            thread.join()
            tasks.task_done()
        for index, text in sorted(dict(print_safe).items(), key=lambda x: x[0]):
            print(text)
            del print_safe[index]
        LOCKER_CONSUME = False

    def consumer_when_full(tasks):
        while consumer_when_full_alive:
            while not tasks.full():
                sleep(0.01)
            consume(tasks)

    consumer_when_full_alive = True
    batch_size, max_boss_num = 100, 0
    print_safe, queue = defaultdict(str), Queue(maxsize=batch_size)
    run(consumer_when_full, arguments={"tasks": queue}, daemon=True)
    # db.drop_tables([Boss, PlayerFight])
    db.create_tables([Boss, PlayerFight])
    max_boss_num = Boss.select(fn.MAX(Boss.num)).scalar() or 0
    index_page = (max_boss_num or start_index) - 1
    # index_page = min_session_number - 1
    while True:
        index_page += 1
        is_present = len(list(Boss.select().where(Boss.num == index_page).limit(1))) > 0
        if is_present:
            print(f"{index_page} already parsed")
            continue
        while queue.full():
            sleep(0.01)
        if index_page > max_boss_num and INDEX_ERROR_COUNT > 10000:
            # consume(tasks)
            print("All validate page has been parsed")
            return
        queue.put(partial(db_insert_pvesession, index_page))
    consumer_when_full_alive = False
    db.close()


def default_player_select(last_days=None, faction=None, join_boss=True, minutes=None) -> ModelSelect:
    query = PlayerFight.select().where((((PlayerFight.server << allowed_servers) &
                                         (PlayerFight.faction == faction if faction else True))))
    if join_boss:
        query = query.join(Boss).where((Boss.minutes > minutes if minutes else True) &
                                       (~Boss.name << blacklist_exact_bosses if blacklist_exact_bosses else True) &
                                       (~(Boss.name.regexp("|".join(blacklist_bosses))) if blacklist_bosses else True) &
                                       (Boss.start > now() - timedelta(days=last_days) if last_days else True))
    return query


def default_boss_select(last_days=None, faction=None, minutes=None) -> ModelSelect:
    return Boss.select().where((Boss.server << allowed_servers) &
                               (Boss.faction == faction if faction else True) &
                               (Boss.minutes > minutes if minutes else True) &
                               (~Boss.name << blacklist_exact_bosses if blacklist_exact_bosses else True) &
                               (~(Boss.name.regexp("|".join(blacklist_bosses))) if blacklist_bosses else True) &
                               (Boss.start > now() - timedelta(days=last_days) if last_days else True))


def classes_ranking(last_days=None, dps_or_heal="dps", faction=None) -> ModelSelect:
    player_select = default_player_select(last_days=last_days, faction=faction, minutes=0.5, join_boss=boss_filter_on)
    total_players_subquery = float(player_select.select(fn.COUNT(fn.DISTINCT(PlayerFight.name))).alias("total_players").scalar())
    per_sec = PlayerFight.dps if dps_or_heal == "dps" else PlayerFight.hps
    query = (player_select
             .select(PlayerFight.class_.alias("class"), fn.AVG(PlayerFight.dps).alias("dps"),
                     fn.MAX(PlayerFight.dps).alias("max_dps"),
                     fn.AVG(PlayerFight.hps).alias("hps"), fn.MAX(PlayerFight.hps).alias("max_hps"),
                     (fn.COUNT(PlayerFight.name.distinct()) / total_players_subquery * 100).cast("int").alias("repartition"))
             .group_by(PlayerFight.class_)
             .order_by(fn.AVG(per_sec).desc()))
    return query


def players_ranking(whitelist_classes: tuple, last_days=None, dps_or_heal="dps", groupby_name=True, faction=None,
                    boss_names=None) -> ModelSelect:
    per_sec = PlayerFight.dps if dps_or_heal == "dps" else PlayerFight.hps
    if groupby_name:  # avg dps
        query = (default_player_select(last_days=last_days, faction=faction, minutes=0.5, join_boss=boss_filter_on)
                 .select(PlayerFight.name.alias("name"), PlayerFight.class_.alias("class"), PlayerFight.faction,
                         fn.AVG(PlayerFight.dps).alias("dps"), fn.MAX(PlayerFight.dps).alias("max_dps"),
                         fn.AVG(PlayerFight.hps).alias("hps"),
                         fn.MAX(PlayerFight.hps).alias("max_hps"), fn.COUNT(PlayerFight.name).alias("count"))
                 .where(
            (PlayerFight.class_ << whitelist_classes) & (Boss.name.regexp("|".join(boss_names)) if boss_names else True))
                 .group_by(PlayerFight.name, PlayerFight.class_, PlayerFight.faction)
                 .order_by(fn.AVG(per_sec).desc()))
    else:  # top dps
        query = (default_player_select(last_days=last_days, faction=faction, minutes=0.5, join_boss=boss_filter_on)
                 .select(PlayerFight.name, PlayerFight.faction, PlayerFight.dps, PlayerFight.hps, PlayerFight.class_,
                         PlayerFight.boss_num, Boss.minutes, Boss.start,
                         Boss.name.alias("boss"))
                 .where(
            (PlayerFight.class_ << whitelist_classes) & (Boss.name.regexp("|".join(boss_names)) if boss_names else True))
                 .order_by(per_sec.desc()))
    return query


def player_rank(name=None, last_days=None) -> Optional[str]:
    name = name.capitalize()
    player = PlayerFight.select().where((PlayerFight.name == name) & (PlayerFight.server << allowed_servers))
    if not player.exists():
        print(name, "player not found")
        return
    player = player[0]
    class_ = player.class_
    faction = player.faction
    df = query_to_df(players_ranking((class_,), last_days=last_days, faction=faction))
    name_row = df[df["name"] == name]
    if len(name_row) == 0:
        if last_days is None:
            print(name, "not any dungeon done yet")
            return
        elif last_days < 7:
            return player_rank(name, 7)
        elif last_days < 30:
            return player_rank(name, 30)
        else:
            return player_rank(name)
    ps_text = ""
    for ps in ["dps", "hps"]:
        if ps == "hps" and class_ not in healers:
            continue
        max_ps = "max_" + ps
        df_ps = df.sort_values(ps, ascending=False).reset_index(drop=True)
        rank_dp = df_ps[df_ps["name"] == name].index[0]
        df_max_ps = df.sort_values(max_ps, ascending=False).reset_index(drop=True)
        rank_max_ps = df_max_ps[df_max_ps["name"] == name].index[0]
        player_ps = int(name_row[ps].iloc[0])
        player_max_ps = int(name_row[max_ps].iloc[0])
        out_of = len(df)
        best_of_ps = round((rank_dp / out_of) * 100, 2)
        best_of_max = round((rank_max_ps / out_of) * 100, 2)
        avg_class_ps = query_to_df(classes_ranking(last_days, faction=faction))
        avg_class_ps = int(avg_class_ps[avg_class_ps["class"] == class_][ps].iloc[0])
        avg_class_max_ps = query_to_df(players_ranking((class_,), last_days=last_days, faction=faction))[
            max_ps]
        avg_class_max_ps = int(avg_class_max_ps.mean())
        ps_text += ("{:<10} {:<15} {:<15} {:<7} top {:<5}%↟ {:<5}%↝ {} {}".format(name,
                                                                                  str(player_ps) + f"-{ps}~" + str(avg_class_ps),
                                                                                  str(player_max_ps) + "-max~" + str(
                                                                                      avg_class_max_ps),
                                                                                  str(rank_max_ps) + "/" + str(out_of),
                                                                                  best_of_max, best_of_ps, faction,
                                                                                  class_)) + "\n"
    taha = fn.SUM(Case(None, ((Boss.name.regexp("|".join(["Tahabata"])), 1),), 0)).alias("Tahabata")
    amount_of_end_game = \
        query_to_df(Boss.select(PlayerFight.name, PlayerFight.server,
                                taha,
                                fn.SUM(Case(None, ((Boss.name.regexp("|".join(["Calindi"])), 1),), 0)).alias("Calindi"),
                                fn.SUM(Case(None, ((Boss.name.regexp("|".join(["Anuhart"])), 1),), 0)).alias("Anuhart"))
                    .join(PlayerFight)
                    .where((Boss.name.regexp("|".join(["Tahabata", "Calindi", "Anuhart"]))) &
                           (Boss.num == PlayerFight.boss_num))
                    .group_by(PlayerFight.name, PlayerFight.server).order_by(taha.desc()))
    amounts = amount_of_end_game[amount_of_end_game["name"] == name][["Tahabata", "Calindi", "Anuhart"]]
    if len(amounts) == 0:
        return ps_text[:-1]
    tahabata, calindi, anuhart = amounts.iloc[0]
    failed = anuhart - tahabata - calindi
    return ps_text + "{} Tahabata with {} fails".format(tahabata, failed)


def is_player_exists(name) -> Optional[PlayerFight]:
    player = list(PlayerFight.select().where((PlayerFight.name == name) & (PlayerFight.server << allowed_servers)).limit(1))
    if len(player) == 0:
        print(name, "player not found")
        return
    return player[0]


def get_bosses_from_player(name, last_days=None, groupby_name=True) -> Optional[ModelSelect]:
    player = is_player_exists(name.capitalize())
    if not player:
        return
    name, faction = player.name, player.faction
    bosses_player_query = (default_boss_select(last_days=last_days, faction=faction)
                           .join(PlayerFight)
                           .where(PlayerFight.name == name)
                           .select_extend(PlayerFight)
                           .order_by(Boss.start.desc()))
    if groupby_name:
        bosses_player_query = (bosses_player_query
                               .select(Boss.name.alias("boss_name"), fn.AVG(PlayerFight.dps).alias("dps"),
                                       fn.AVG(PlayerFight.hps).alias("hps"), fn.COUNT(Boss.name))
                               .group_by(Boss.name)
                               .order_by(fn.COUNT(Boss.name).desc()))
    return bosses_player_query


def get_teammates_from_player(name, last_days=None) -> Optional[ModelSelect]:
    player = is_player_exists(name.capitalize())
    if not player:
        return
    name, faction = player.name, player.faction
    boss_nums = (default_player_select(last_days=last_days, faction=faction)
                 .select(Boss.num)
                 .where(PlayerFight.name == name))
    teammates = (PlayerFight.select(PlayerFight.name, fn.COUNT(PlayerFight.name))
                 .where((PlayerFight.boss_num.in_(boss_nums)))
                 .group_by(PlayerFight.name)
                 .order_by(fn.COUNT(PlayerFight.name).desc()))
    return teammates


def bosses_ranking(last_days, faction=None, sort_key="name"):
    order_by_attr = fn.COUNT(getattr(Boss, sort_key)) if sort_key == "name" else fn.AVG(getattr(Boss, sort_key))
    return (default_boss_select(last_days, faction)
            .select(Boss.name, fn.COUNT(Boss.name).alias("amount"), fn.AVG(Boss.minutes).alias("avg_minutes"))
            .group_by(Boss.name)
            .order_by(order_by_attr.desc()))


def bosses_players_value_ranking(last_days=None, classes=all_classes, bosses=None, groupeby_name=False,
                                 dps_or_heal="dps", faction=None) -> ModelSelect:
    ps = PlayerFight.dps if dps_or_heal == "dps" else PlayerFight.hps
    case_statements = [fn.AVG(Case(None, ((PlayerFight.class_ == class_, ps),))).alias(class_ + " " + dps_or_heal)
                       for class_ in classes]
    query = (default_boss_select(last_days=last_days, minutes=0.5, faction=faction)
             .join(PlayerFight)
             .where(Boss.num << bosses if bosses else True))
    if groupeby_name:
        query = (query.select(Boss.name.alias("boss_name"), fn.COUNT(Boss.name).alias("amount players"),
                              fn.AVG(Boss.minutes).alias("avg_minutes for each players"),
                              fn.AVG(ps).alias("team_average_" + dps_or_heal), *case_statements)
                 .group_by(Boss.name)
                 .order_by(fn.AVG(ps).desc()))
    else:
        query = (query.select(fn.AVG(ps).alias("team_average_" + dps_or_heal), *case_statements)
                 .select_extend(Boss)
                 .group_by(Boss.num)
                 .order_by(fn.AVG(ps).desc()))
    return query


def top_team_dps_on(name, last_days=None) -> Optional[str]:
    player = is_player_exists(name.capitalize())
    if player is None:
        return
    name, class_, faction, server = str(player.name), player.class_, player.faction, player.server
    player_bosses = get_bosses_from_player(name, groupby_name=False)
    if player_bosses is None:
        if last_days is None:
            exit("not any dungeons yet")
        elif last_days < 7:
            return top_team_dps_on(name, 7)
        elif last_days < 30:
            return top_team_dps_on(name, 30)
        else:
            return top_team_dps_on(name)
    # Subquery to get the average team DPS for each boss_num
    avg_team_dps = bosses_players_value_ranking(classes=[], faction=faction)
    # Query to calculate the average team DPS and count team computed for each player
    average_team_dps = query_to_df((PlayerFight
                                    .select(PlayerFight.name, PlayerFight.server,
                                            fn.AVG(avg_team_dps.c.team_average_dps).cast("int").alias("average_team_dps"),
                                            fn.COUNT(PlayerFight.boss_num).alias("team counted"))
                                    .join(avg_team_dps, on=(PlayerFight.boss_num == avg_team_dps.c.num))
                                    .where(PlayerFight.class_ == class_)
                                    .group_by(PlayerFight.name, PlayerFight.server)
                                    .alias("average_team_dps")
                                    .order_by(fn.AVG(avg_team_dps.c.team_average_dps).desc())))
    avg_all_team_dps = int(average_team_dps["average_team_dps"].mean())
    row = average_team_dps.loc[(average_team_dps["name"] == name) & (average_team_dps["server"] == server), "average_team_dps"]
    top, avg_player_team_dps = row.index[0], row.iloc[0]
    out_of = len(average_team_dps)
    best_of = round((top / out_of) * 100, 2)
    return "{:<10} {:<20} {:<15} top_team {}% {} {}".format(name, str(avg_player_team_dps) + "-team_dps~" + str(
        avg_all_team_dps), str(top) + "/" + str(out_of), best_of, faction, class_)


def spot_admin() -> tuple[ModelSelect, ModelSelect]:
    bosses_admin_spotted = (Boss.select(Boss.num, Boss.name, fn.COUNT(PlayerFight.name))
                            .join(PlayerFight)
                            .group_by(Boss.num)
                            .order_by(fn.COUNT(PlayerFight.name).desc())
                            .having(fn.COUNT(PlayerFight.name) >= 7))
    players_admin_spotted_with_num = (PlayerFight.select()
                                      .where((PlayerFight.boss_num.in_(bosses_admin_spotted.select(Boss.num))) &
                                             ((PlayerFight.dps + PlayerFight.hps) < 50)))
    players_admin_spotted = (players_admin_spotted_with_num
                             .select(PlayerFight.name, PlayerFight.server, PlayerFight.faction, fn.COUNT(PlayerFight.name),
                                     (fn.AVG(PlayerFight.dps) + fn.AVG(PlayerFight.dps)).alias("avg_vps"))
                             .group_by(PlayerFight.name, PlayerFight.server, PlayerFight.faction)
                             .order_by(fn.COUNT(PlayerFight.name).desc()))
    admins: dict[tuple, list] = defaultdict(list)
    for player in players_admin_spotted_with_num:
        admins[(player.name, player.server, player.boss_num)].append(player)
    for _, players in sorted(admins.items(), key=lambda x: -len(x[1])):
        for player in players:
            boss_name = bosses_admin_spotted.select(Boss.name).where(Boss.num == player.boss_num).get().name
            print(f"https://{url_api}/PvESession/{player.boss_num}", player.name, player.server, len(players), boss_name)
    return players_admin_spotted, players_admin_spotted_with_num


def player_infos(player_name, last_days=None) -> None:
    teammates = query_to_df(get_teammates_from_player(player_name, last_days))  # todo isolate instances
    print(player_rank(player_name, last_days))
    print(top_team_dps_on(player_name, last_days))
    average_dps_n_amount_bosses_done_for_a_player = query_to_df(get_bosses_from_player(player_name, last_days))
    all_bosses_done_for_a_player = query_to_df(get_bosses_from_player(player_name, last_days, groupby_name=False))
    if not all_bosses_done_for_a_player.empty:
        print(player_name, "10 last bosses")
        print(all_bosses_done_for_a_player["start"][:10])
    _ = "debug breakpoint"


def fight_infos(num) -> ModelSelect:
    return PlayerFight.select().where(PlayerFight.boss_num == num).join(Boss).select_extend(Boss)


def init_plt(figsize=(16, 9), curve_color="#0F1623", title=""):
    from matplotlib import pyplot as plt
    # plt.rcParams['toolbar'] = 'None'
    plt.rcParams["figure.figsize"] = figsize
    plt.rcParams["axes.facecolor"] = curve_color
    plt.rcParams["axes.edgecolor"] = "white"
    plt.rcParams["axes.labelcolor"] = "white"
    plt.rcParams["axes.titlecolor"] = "white"
    fig, ax = plt.subplots()
    fig.patch.set_facecolor(curve_color)
    ax.tick_params(axis="x", colors="white")
    ax.tick_params(axis="y", colors="white")
    ax.xaxis.set_minor_locator(plt.NullLocator())
    plt.title(title)
    return plt, ax, fig


def plot_players_over_time_tagged():
    start = Boss.select(fn.MIN(Boss.start)).scalar().replace(hour=0, minute=0, second=0, microsecond=0)
    end = Boss.select(fn.MAX(Boss.start)).scalar().replace(hour=0, minute=0, second=0, microsecond=0)
    cursor = start
    daily_player = DataFrame(columns=["daily_player"])
    total_player = DataFrame(columns=["total_player"])
    unique_players = set()
    while cursor < end:
        next_day = cursor + timedelta(days=1)
        daily_query = PlayerFight.select(PlayerFight.name).join(Boss).where(Boss.start.between(cursor, next_day) &
                                                                            (PlayerFight.server << allowed_servers)).distinct()
        unique_players |= set(player.name for player in daily_query)
        daily_player.loc[cursor] = daily_query.count()
        total_player.loc[cursor] = len(unique_players)
        cursor = next_day
        print(cursor.date())
    plt, ax, fig = init_plt(title="Players over time")
    daily_player["daily_player"].plot(kind="line", label="daily_player")
    total_player["total_player"].plot(kind="line", label="total_player")
    date_format = "%Y-%m-%d"
    ax.yaxis.tick_right()
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter(date_format))
    ax.xaxis.set_major_locator(MultipleLocator(6))
    plt.setp(ax.get_xticklabels(), rotation=10, fontsize=10)
    ax.xaxis.set_minor_locator(plt.NullLocator())
    plt.xlabel("Date"), plt.ylabel("Unique player"), [text.set_color("white") for text in plt.legend().get_texts()]
    plt.show()


def plot_classes_vps_over_time(top=None, last_days=None):
    start = (now() - timedelta(days=last_days) if last_days
             else Boss.select(fn.MIN(Boss.start)).scalar().replace(hour=0, minute=0, second=0, microsecond=0))
    end = Boss.select(fn.MAX(Boss.start)).scalar().replace(hour=0, minute=0, second=0, microsecond=0)
    cursor = start
    classes_ranking_over_time = DataFrame(columns=list(all_classes))
    while cursor < end:
        next_day = cursor + timedelta(days=1)
        if top:
            case_statements = [Case(None, ((PlayerFight.class_ == class_, (PlayerFight.dps + PlayerFight.hps)),)
                                    ).alias(class_) for class_ in all_classes]
            # case_statements += [PlayerFight.name, PlayerFight.boss_num]
            query = (default_player_select(minutes=0.5, join_boss=boss_filter_on, last_days=last_days)
                     .where(Boss.start.between(cursor, next_day))
                     .select(*case_statements)
                     .order_by((PlayerFight.dps + PlayerFight.hps).desc()))
            df = query_to_df(query).replace({None: np.nan})
            dps_dict = {
                class_: 0 if np.isnan(df[class_].nlargest(top).mean()) else df[class_].nlargest(top).mean() for class_ in df.columns}
        else:
            query = (default_player_select(minutes=0.5, join_boss=boss_filter_on, last_days=last_days)
                     .select(PlayerFight.class_.alias("class"),
                             (fn.AVG(PlayerFight.dps) + fn.AVG(PlayerFight.hps)).alias("vps"))
                     .where(Boss.start.between(cursor, next_day))
                     .group_by(PlayerFight.class_)
                     .order_by(fn.AVG(PlayerFight.dps) + fn.AVG(PlayerFight.hps)))
            classes_ranking_df = query_to_df(query).replace({None: np.nan})
            dps_dict = {
                class_: vps if np.isnan(vps) else vps for class_, vps in zip(classes_ranking_df["class"], classes_ranking_df["vps"])}
        print(cursor.date())
        classes_ranking_over_time.loc[cursor.date()] = dps_dict
        cursor = next_day
    plt, ax, fig = init_plt(title="Classes{} values per second average per day".format(f" top {top}" if top else ""))
    for class_ in all_classes:
        classes_ranking_over_time[class_].plot(kind="line", label=class_)
    date_format = "%Y-%m-%d"
    ax.yaxis.tick_right()
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter(date_format))
    ax.xaxis.set_major_locator(MultipleLocator((end - start).days // 20))
    plt.setp(ax.get_xticklabels(), rotation=15, fontsize=10)
    ax.xaxis.set_minor_locator(plt.NullLocator())
    plt.xlabel("Date"), plt.ylabel("{}Value per second".format(f"Top {top} " if top else "", "Value per second"))
    [text.set_color("white") for text in plt.legend().get_texts()]
    plt.show()


def get_random_player_name(last_days=None, faction=None):
    return choice(
        list(default_player_select(last_days, faction).select(PlayerFight.name).distinct().where(PlayerFight.class_ << all_classes))).name


if __name__ == "__main__":
    # last_days = None
    last_days = 15
    # scrap_n_update_db()

    # player_name = get_random_player_name()
    # player_infos(player_name, last_days)
    # players_admin_spotted, players_admin_spotted_with_num = map(query_to_df, spot_admin())
    # query_to_df(players_ranking(all_classes, last_days, groupby_name=True).order_by(fn.COUNT(PlayerFight.name).desc()))
    # boss_instance_info = query_to_df(fight_infos(4000000))
    # classes_ranking_sorted_by_dps = query_to_df(classes_ranking(last_days))
    # players_ranking_sorted_by_dps = query_to_df(players_ranking(all_classes, last_days))
    # players_ranking_sorted_by_hps = query_to_df(players_ranking(all_classes, last_days, dps_or_heal="hps"))
    # _class__players_ranking_sorted_by_dps = query_to_df(players_ranking(("Templar",), last_days, faction="Asmodian"))
    # dps_ranking_for_each_boss = query_to_df(players_ranking(all_classes, last_days, groupby_name=False))
    # dps_ranking_for_given_bosses = query_to_df(players_ranking(all_classes, last_days, groupby_name=True, boss_names=["Taha"]))
    # amount_bosses_ranking = query_to_df(bosses_ranking(last_days, sort_key="name"))
    # time_elapsed_bosses_ranking = query_to_df(bosses_ranking(last_days, sort_key="minutes"))
    # players_ranking_for_killed_bosses = query_to_df(
    #     players_ranking(all_classes, last_days, groupby_name=True).order_by(fn.COUNT(PlayerFight.name).desc()))
    # players_ranking_for_killed_named_bosses = query_to_df(
    #     players_ranking(all_classes, last_days, groupby_name=True, boss_names=["Taha"]).order_by(fn.COUNT(PlayerFight.name).desc()))
    # all_bosses_sorted_by_date = query_to_df(default_boss_select(last_days).order_by(Boss.start))
    # all_average_team_dps_n_dps_for_each_teammate = query_to_df(bosses_players_value_ranking(last_days))
    # all_average_team_hps_n_hps_for_each_teammate = query_to_df(bosses_players_value_ranking(last_days, dps_or_heal="hps"))
    # average_team_dps_n_average_class_dps_for_each_boss = query_to_df(bosses_players_value_ranking(last_days, groupeby_name=True))
    # plot_players_over_time_tagged()
    plot_classes_vps_over_time(top=200, last_days=60)
    plot_classes_vps_over_time()
    _ = "debug breakpoint"
