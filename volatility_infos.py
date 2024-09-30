import locale
import sys
import threading
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import talib
import matplotlib
from pandas import DataFrame
from matplotlib import ticker, figure, axis
from matplotlib.widgets import Cursor

data_needed_before = 60  # candles needed before start_timer for exponential moving average calculation
groupby_column = "volatilityOC60ema"
chart_names = ["last_week", "last_month", "last_year"]

chart_colors = "bgr"
week_order = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
locale.setlocale(locale.LC_ALL, "fr_FR.utf8")
df_last_year = pd.read_csv("2022_BUSDBTC_1m.csv", sep=";")
end_timer = datetime(year=2023, month=1, day=1) - timedelta(minutes=1)
df_last_month = df_last_year[(str(end_timer - timedelta(days=31) - timedelta(minutes=data_needed_before))
                              <= df_last_year["time"])]
df_last_week = df_last_year[(str(end_timer - timedelta(weeks=1) - timedelta(minutes=data_needed_before)) <= df_last_year["time"])]
current = datetime.now()
day_name = current.strftime("%A")


def init_gui(axis_color, fullscreen=True, title="", date_format=None, qt=True, n_subplots=1) -> tuple["plt", axis, figure]:
    def exit_event(event):
        if event.button == 3:
            print(event)
            pyplot.close("all")
            sys.exit()

    import matplotlib.pyplot as pyplot
    face_color = "#0F1623"
    pyplot.rcParams["figure.figsize"] = (16, 8)
    pyplot.rcParams["keymap.zoom"].append("a")
    pyplot.rcParams["keymap.back"].append("²")
    if "left" in pyplot.rcParams["keymap.back"]:
        pyplot.rcParams["keymap.back"].remove("left")
        pyplot.rcParams["keymap.forward"].remove("right")
    pyplot.rcParams["text.color"] = "white"
    pyplot.rcParams["axes.facecolor"] = face_color
    pyplot.rcParams["axes.titley"] = 1.0
    pyplot.rcParams["axes.titlepad"] = -85
    # matplotlib.use("module://backend_interagg")
    if qt and threading.current_thread() == threading.main_thread():
        # print(matplotlib.get_backend())
        matplotlib.use("Qt5agg")

    fig, axs = pyplot.subplots(n_subplots)
    if n_subplots == 1:
        axs = [axs]
    for i in range(len(fig.axes)):
        ax = axs[i]
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()
        ax.spines["bottom"].set_color(axis_color)
        ax.spines["top"].set_color(axis_color)
        ax.spines["right"].set_color(axis_color)
        ax.spines["left"].set_color(axis_color)
        ax.tick_params(axis="x", colors=axis_color)
        ax.tick_params(axis="y", colors=axis_color)
        if date_format is not None:
            if date_format == "":
                date_format = "%Y-%m-%d %Hh%mm"
            ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter(date_format))
        pyplot.connect("motion_notify_event", func=Cursor(ax, color="black", linewidth=0.5))
    if fig is None:
        fig: pyplot.figure = pyplot.figure()
    if fullscreen:
        fig.canvas.manager.full_screen_toggle()
    fig.patch.set_facecolor(face_color)
    fig.canvas.mpl_connect("button_press_event", exit_event)
    fig.suptitle(title)
    return pyplot, axs, fig


def add_indicators(df, is_ascending: Optional[bool] = None, ordered_column: str = "time") -> Optional[DataFrame]:
    def ma(array, n):
        ma_ = np.cumsum(array, dtype=float)
        ma_[n:] = ma_[n:] - ma_[:-n]
        return np.append(np.full([n - 1], np.nan), ma_[n - 1:] / n)

    def ema(array, n):
        ema_ = np.full_like(array, np.nan, dtype=float)
        alpha, ema_[0] = 2 / (n + 1), array[0]
        for t in range(1, len(array)):
            ema_[t] = (1 - alpha) * ema_[t - 1] + alpha * array[t]
        return ema_

    if not len(df):
        return
    df = df.copy()
    # to add correct indicator values, data has to be ascending
    is_reversed = False
    if not is_ascending and ordered_column in df.columns and df[ordered_column].iloc[0] > df[ordered_column].iloc[1]:
        df = df[::-1]
        is_reversed = True
    df["ohlc"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    df["volatilityOC"] = (df["close"] / df["open"] - 1) * 100 * 100
    abs_volatility_oc_array = df["volatilityOC"].apply(abs).to_numpy()
    f = [ma, ema, talib.EMA]  # ema <=> talib.EMA
    df["volatilityOC" + str(data_needed_before) + "ema"] = f[1](abs_volatility_oc_array, data_needed_before)
    if is_reversed:  # same input order
        df = df[::-1]
    return df


def add_data_times(df, column="time", index=False) -> DataFrame:
    df = df.copy()
    date_emplacement = df.index if index else df[column]
    df["datetime"] = pd.to_datetime(date_emplacement, format="%Y-%m-%d %H:%M:%S")
    df["month"], df["day_name"], df["day"], df["hour"], df["minute"], df["second"] = (
        df["datetime"].apply(lambda x: x.month),
        df["datetime"].apply(lambda x: x.strftime("%A")),
        df["datetime"].apply(lambda x: x.day),
        df["datetime"].apply(lambda x: x.hour),
        df["datetime"].apply(lambda x: x.minute),
        df["datetime"].apply(lambda x: x.second))
    return df


def str_zfill(x):
    return str(x).zfill(2)


def plot_grouped_by_dayname_hour_minute(ax):
    for i in range(len(dataframes)):
        df = dataframes[i].copy()
        df = df.groupby([df.day_name, df.hour, df.minute]).mean(numeric_only=True)
        df = df.loc[week_order]
        df = df.reset_index()
        df = df[(df["day_name"] == day_name)]
        df.index = df["day_name"] + " " + df["hour"].apply(str_zfill) + "h" + df["minute"].apply(str_zfill) + "m"
        ax.plot(df.index, df[groupby_column], "-" + chart_colors[i % len(chart_colors)], label=chart_names[i], linewidth=0.5)
        if i == 0:
            x = "{} {}h{}m".format(day_name, str_zfill(current.hour), str_zfill(current.minute))
            ax.axvline(x=x, color="cyan", linestyle="--", linewidth=0.5)
            line = ax.axhline(y=round(df.loc[x][groupby_column], 3), color="cyan", linestyle="--", linewidth=0.5)
            ax.annotate(str(line.get_ydata()[0]), xy=(0, line.get_ydata()[0]), xycoords="data", xytext=(-5, -5),
                        textcoords="offset points")


def plot_grouped_by_hour_minute(ax):
    for i in range(len(dataframes)):
        df = dataframes[i].copy()
        df = df.groupby([df.hour, df.minute]).mean(numeric_only=True)
        df.index = map(lambda t: str(t[0]).zfill(2) + "h" + str(t[1]).zfill(2) + "m", df.index)
        ax.plot(df.index, df[groupby_column], "-" + chart_colors[i % len(chart_colors)], label=chart_names[i], linewidth=0.5)
        if i == 0:
            x = "{:02d}h{:02d}m".format(current.hour, current.minute)
            ax.axvline(x=x, color="cyan", linestyle="--", linewidth=0.5)
            line = ax.axhline(y=round(df.loc[x][groupby_column], 3), color="cyan", linestyle="--", linewidth=0.5)
            ax.annotate(str(line.get_ydata()[0]), xy=(0, line.get_ydata()[0]), xycoords="data", xytext=(-5, -5),
                        textcoords="offset points")


if __name__ == "__main__":
    plt_, axs_, fig_ = init_gui(axis_color="#FFFFFFBB", n_subplots=2, fullscreen=False,
                                title="volatilityOC60ema grouped by dayname_hour_minute & hour_minute")
    dataframes = [add_data_times(add_indicators(df)) for df in [df_last_week, df_last_month, df_last_year]]
    plot_grouped_by_dayname_hour_minute(axs_[0])
    plot_grouped_by_hour_minute(axs_[1])
    for ax_ in axs_:
        ax_.xaxis.set_major_locator(ticker.MultipleLocator(100))
        plt_.setp(ax_.get_xticklabels(), rotation=10, fontsize=10)
        ax_.legend(loc="upper left")
    plt_.show()

# get_candles_data function code #####

# from asyncio import sleep
# from inspect import currentframe, getargvalues
# import os
# import traceback
# from binance.exceptions import BinanceAPIException
# from pandas.errors import EmptyDataError
# import requests
# from typing import Callable
# from Introspection import recall_current_function
# from Threads import run
# from Times import elapsed_seconds, now, to_datetime
# from Util import add_rows_dataframe
# df_last_year = lambda: get_candles_data("BTCBUSD", interval="1m",
#                                         start_timer=end_timer - timedelta(days=366) - timedelta(minutes=data_needed_before),
#                                         end_timer=end_timer, file_name="2022_BUSDBTC_1m.csv")
# df_last_month = lambda: get_candles_data("BTCBUSD", interval="1m",
#                                          start_timer=end_timer - timedelta(days=30) - timedelta(minutes=data_needed_before),
#                                          end_timer=end_timer, file_name="2022_BUSDBTC_1m.csv")
# df_last_week = lambda: get_candles_data("BTCBUSD", interval="1m",
#                                         start_timer=end_timer - timedelta(weeks=1) - timedelta(minutes=data_needed_before),
#                                         end_timer=end_timer, file_name="2022_BUSDBTC_1m.csv")
# A messy function not clean but well performing
# def get_candles_data(pair: str,
#                      interval,
#                      start_timer: datetime,
#                      end_timer: datetime,
#                      ascending=False,
#                      debug=True,
#                      fastest_but_file_not_safe=False,
#                      file_name: str = None) -> Optional[DataFrame]:
#
#     def now(utc=False, offset_h=0, offset_m=0, offset_s=0, with_ms=True) -> datetime:
#         offset = timedelta(hours=offset_h, minutes=offset_m, seconds=offset_s)
#         datetime_now = offset + (datetime.utcnow() if utc else datetime.now())
#         return datetime_now if with_ms else datetime_now.replace(microsecond=0)
#
#     def to_datetime(obj, pattern: str = "%Y/%m/%d %H:%M:%S") -> datetime:
#         if type(obj) is datetime:
#             return obj
#         try:
#             return datetime.fromtimestamp(int(obj))
#         except (ValueError, AttributeError, TypeError):
#             default_value = pattern == "%Y/%m/%d %H:%M:%S"
#             str_obj = str(obj).replace("-", "/") if default_value else str(obj)
#             return datetime.strptime(str_obj, pattern)
#
#     def add_rows_dataframe(df: DataFrame, rows: dict[str, list | tuple], bottom=True) -> DataFrame:
#         """ slow, add all lines at the same time"""
#         rows = {k: [v] if type(v) not in (list, tuple, set) else v for (k, v) in rows.items()}
#         concat_df = [df, pd.DataFrame(rows)][::1 if bottom else -1]
#         # return pd.concat(concat_df).drop_duplicates().reset_index(drop=True)
#         return pd.concat(concat_df).reset_index(drop=True)
#
#     def elapsed_seconds(date_time: datetime):
#         return (datetime.now() - date_time).total_seconds()
#
#     def get_years_months(start_date, end_date):
#         if start_date > end_date:
#             return []
#         years_months = []
#         cursor = start_date
#         starting_date = cursor
#         while cursor <= end_date:
#             old_cursor = cursor
#             cursor = cursor + timedelta(days=1)
#             if cursor.month != old_cursor.month and cursor < end_date:
#                 years_months.append([starting_date, cursor - timedelta(seconds=1)])
#                 starting_date = cursor
#         if starting_date < end_date:
#             years_months.append([starting_date, end_date])
#         return years_months
#
#     def interval_to_timedelta(interval):
#         if "m" in interval:
#             time_delta_interval = timedelta(minutes=int(interval[:interval.index("m")]))
#             freq = "T"
#         elif interval == "1s":
#             time_delta_interval = timedelta(seconds=1)
#             freq = "s"
#         else:
#             raise "interval problem"
#         return time_delta_interval, freq
#
#     def pairinterval_to_candle_file_name(pair, interval, start_timer=""):
#         year_month = ("_" + str(start_timer)[:7]) if interval == "s" else ""
#         file_name = "{}{}_{}{}.csv".format(CANDLES_PATH, pair, interval, year_month)
#         file_name_missing_data = "{}{}_{}{}_missing.csv".format(CANDLES_PATH, pair, interval, year_month)
#         return file_name, file_name_missing_data
#
#     def is_file_exist(path: str) -> bool:
#         """ Due to concurrency, after an is_existing call, it may be possible that the file doesn't exist,
#         in this case, use a try-catch exception when the file is used """
#         return os.path.exists(path)
#
#     def recall_current_function(sleep_time):
#         """ Be careful to not modify given function's args within the local context otherwise the call will be with thoses modified args """
#         sleep(sleep_time)
#         calling_frame = currentframe().f_back
#         function = calling_frame.f_globals[calling_frame.f_code.co_name]
#         arg_values = getargvalues(calling_frame)
#         called_args = {arg_name: arg_values.locals[arg_name] for arg_name in arg_values[0]}
#         return function(**called_args)
#
#     def run(fun: Callable, arguments: dict = {}, wait_a_bit: float = 0.0, alert_if_error=True, print_if_error=True, name=None) \
#             -> threading:
#         """
#         run(playback.play, arguments={"audio_segment": sound})
#         """
#
#         def aux():
#             # noinspection PyBroadException
#             try:
#                 fun(**arguments)
#             except Exception:
#                 if print_if_error:
#                     print(traceback.format_exc(), file=sys.stderr)
#                     print(fun.__name__, file=sys.stderr)
#
#         thread = threading.Thread(target=aux)
#         thread.name = name if name else fun.__name__
#         thread.start()
#         sleep(wait_a_bit)
#         return thread
#
#     def _fill_candle(candle_df, cursor_start_time):  # 1 weight
#         # while WEIGHT.sum_update() >= 1000:
#         #     print("WEIGHT overloaded - wait", WEIGHT.sum_update())
#         #     sleep(1)
#         # try:
#         #     WEIGHT.put(1)
#         datas = CLIENT.get_klines(symbol=pair, interval=interval, limit=1000,
#                                   startTime=int(cursor_start_time.timestamp()) * 1000)
#         # except (BinanceAPIException, requests.exceptions.ReadTimeout, ConnectionError):
#         #     return None
#         if datas is None or len(datas) == 0:
#             return None
#         start = now()
#         open_time, _open, high, low, close, volume, close_time, quote_asset_volume, trades, taker_buy_base_asset_volume, taker_buy_quote_asset_volume, _ = list(
#             zip(*datas))
#         open_time = list(map(lambda x: str(to_datetime(int(x) / 1000)), open_time))
#         candle_df = add_rows_dataframe(candle_df, {"time": open_time,
#                                                    "open": _open,
#                                                    "high": high,
#                                                    "low": low,
#                                                    "close": close,
#                                                    "volume": volume,
#                                                    # "devise_volume": quote_asset_volume,   # not redundant but little used, commented to reduce file size. Used to calculate the average price of a candle: devise_volume / volume
#                                                    "trades": trades})
#         candle_df = candle_df.astype({column: float for column in candle_df.columns if column != "time" and column != "trades"})
#         if not len(candle_df):
#             return None
#         candle_df = candle_df[(candle_df["time"] <= str(end_timer))]
#         next_cursor_start_time = to_datetime(candle_df["time"].iloc[-1]) + time_delta_interval
#         if debug:
#             print(elapsed_seconds(start), end=" ")
#         min_inserted, max_inserted = open_time[0], open_time[-1]
#         return candle_df, next_cursor_start_time, min_inserted, max_inserted
#
#     def organize_df(df) -> DataFrame:
#         df = df[(str(start_timer) <= df["time"])]
#         df = df[(df["time"] <= str(end_timer))]
#         if year_month:
#             df = df[(df["time"].str.contains(year_month[1:]))]
#         df = df.drop_duplicates(subset=["time"]).sort_values("time", ascending=ascending)
#         return df
#
#     year_month = ""
#     years_months = get_years_months(start_timer, end_timer)
#     if len(years_months) > 1:
#         df = pd.DataFrame()
#         for (s, e) in years_months:
#             df = pd.concat((df, get_candles_data(pair, interval, s, e, ascending, debug, fastest_but_file_not_safe,
#                                                  file_name))).reset_index(drop=True)
#         return organize_df(df)
#
#     start = now()
#     file_name_missing_data = None
#
#     time_delta_interval, freq = interval_to_timedelta(interval)
#     if freq == "s":
#         year_month = "_" + str(start_timer)[:7]
#     # if debug:
#     #     print("get_candles", pair, interval, start_timer, end_timer)
#     #     return file, file_name_missing_data
#     if file_name is None:
#         file_name, file_name_missing_data = pairinterval_to_candle_file_name(pair, interval, start_timer)
#     second = start_timer.second if interval == "1s" else 0
#     start_timer = start_timer.replace(second=second, microsecond=0)
#     end_timer = end_timer.replace(second=second, microsecond=0)
#     cursor_start_time_old: Optional[datetime] = None
#     complete_df = DataFrame()
#     return_df = DataFrame()
#     times_wanted = {str(start_timer)}.union(
#         set(map(str, pd.date_range(start=start_timer, end=end_timer - time_delta_interval, freq=time_delta_interval)
#                 .to_pydatetime().tolist())))
#     data_not_available = pd.DataFrame({'ignore_data': []})
#     if file_name_missing_data and is_file_exist(file_name_missing_data):
#         data_not_available = pd.read_csv(file_name_missing_data, sep=";")
#     if is_file_exist(file_name):
#         try:
#             csv_df = pd.read_csv(file_name, sep=";")
#         except EmptyDataError:
#             # print(EmptyDataError)
#             return recall_current_function(1)
#         complete_df = csv_df.loc[:, csv_df.columns != "Unnamed: 0"]
#         if set(complete_df["time"]).union(set(data_not_available["ignore_data"])).issuperset(times_wanted):
#             return organize_df(complete_df)
#         left_times_wanted = sorted(
#             times_wanted.union(set(data_not_available["ignore_data"])).difference(complete_df["time"]))
#         print(left_times_wanted[0], "...", left_times_wanted[-1], len(left_times_wanted))
#
#     min_inserted = None
#     next_cursor_start_time = None
#     cursor_start_time = start_timer
#     # while cursor_start_time <= end_timer and cursor_start_time <= now() - timedelta(minutes=1):
#     while cursor_start_time <= end_timer and cursor_start_time <= now():
#         if elapsed_seconds(start) > 60:
#             debug = True
#         if len(complete_df):
#             unseen_timers = times_wanted.difference(set(data_not_available["ignore_data"])).difference(complete_df["time"])
#             if len(unseen_timers) == 0:
#                 # Data filled
#                 break
#             smallest_unseen_timer = min(unseen_timers)
#             # biggest_unseen_timer = max(unseen_timers)
#             cursor_start_time = datetime.strptime(smallest_unseen_timer, "%Y-%m-%d %H:%M:%S")
#             if debug:
#                 print(smallest_unseen_timer, end=" ")
#             candle_data_is_not_available = cursor_start_time == cursor_start_time_old
#             if candle_data_is_not_available and min_inserted:
#                 ignore_data = set(map(str, pd.date_range(start=smallest_unseen_timer,
#                                                          end=to_datetime(min_inserted) - time_delta_interval,
#                                                          freq=freq).to_pydatetime().tolist()))
#                 data_not_available = add_rows_dataframe(data_not_available, {"ignore_data": list(ignore_data)})
#                 cursor_start_time = to_datetime(next_cursor_start_time)
#                 continue
#             cursor_start_time_old = cursor_start_time
#         results = _fill_candle(complete_df, cursor_start_time)
#         if results is None:
#             break
#         complete_df, next_cursor_start_time, min_inserted, max_inserted = results
#         cursor_start_time = next_cursor_start_time
#         if set(complete_df["time"]).union(set(data_not_available["ignore_data"])).issuperset(times_wanted):
#             break
#         if debug:
#             print(end_timer - cursor_start_time, "left")
#     if len(complete_df):
#         return_df = organize_df(complete_df)
#
#     def aux():
#         """ Can reset file ? """
#         if "time" in complete_df.columns:
#             df = complete_df.drop_duplicates(subset=["time"]).sort_values("time")
#             # complete_df.to_csv(file_name, sep=";", date_format="%Y-%m-%d %H:%M:%S")
#             df.to_csv(file_name, sep=";", date_format="%Y-%m-%d %H:%M:%S", index=False)
#             data_not_available.to_csv(file_name_missing_data, sep=";", index=False)
#
#     run(aux) if fastest_but_file_not_safe else aux()
#     return return_df
