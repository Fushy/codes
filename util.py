import itertools
import sys
import threading
import traceback
from collections.abc import Iterable
from datetime import datetime, timedelta
from threading import Thread
from time import sleep
from typing import Callable, Type

import pandas as pd
from colorama import Back, Fore, init, Style
from openpyxl.reader.excel import load_workbook
from pandas import DataFrame
from peewee import Model

def reverse_dict(dict_: dict) -> dict:
    """ Reverse the self.questions_answers dictionary. Keys become values, and values become keys """
    new_keys = sorted(set(itertools.chain.from_iterable(dict_.values())))
    return {new_key: [key for (key, values) in dict_.items() if new_key in values] for new_key in new_keys}
    # return {tuple(v) if type(v) is Iterable else v: k for (k, v) in d.items()}

def from_excel_to_dataframe(file_name: str) -> DataFrame:
    workbook = load_workbook(file_name)
    data = workbook.active.values
    headers = next(data)
    return pd.DataFrame(data, columns=headers)

def run(fun: Callable, arguments: dict = {}, wait_a_bit: float = 0.0, alert_if_error=True, print_if_error=True, name=None,
        daemon=False, ignore_error=False) -> threading:
    """
    run(playback.play, arguments={"audio_segment": sound})
    """

    def aux():
        if ignore_error:
            try:
                fun(**arguments)
            except Exception:
                if print_if_error:
                    print(traceback.format_exc(), file=sys.stderr)
                    print(name or fun.__name__, file=sys.stderr)
                # if alert_if_error:
                #     Alert.alert(str(name or fun.__name__) + "\n\n" + traceback.format_exc(), level=3)
        else:
            fun(**arguments)

    thread = Thread(target=aux, daemon=daemon)
    if name:
        thread.name = name
    elif getattr(fun, "__name__", None):
        thread.name = fun.__name__
    thread.start()
    sleep(wait_a_bit)
    return thread


def query_to_df(query) -> DataFrame:
    return DataFrame(query.dicts())


def now(utc=False, offset_h=0, offset_m=0, offset_s=0, with_ms=True) -> datetime:
    offset = timedelta(hours=offset_h, minutes=offset_m, seconds=offset_s)
    datetime_now = offset + (datetime.utcnow() if utc else datetime.now())
    return datetime_now if with_ms else datetime_now.replace(microsecond=0)


def printc(text: str, color="green", background_color=None, attributes: Iterable[str] = ["NORMAL"]):
    init()
    style = getattr(Fore, color.upper()) if color != "" else ""
    if background_color:
        style += getattr(Back, background_color.upper())
    if attributes:
        " ".join([getattr(Style, attribute.upper()) for attribute in attributes])
    print("{}{}{}".format(style, text, Style.RESET_ALL))


def is_iter_but_not_str(element):
    """ Si le type de l'objet peut être parcouru et n'est pas de type str"""
    return isinstance(element, Iterable) and not isinstance(element, str)


def get_columns_name_model(model: Type[Model]):
    return list(model._meta.fields)


def fill_rows(model: Type[Model], columns_order: list[str], values: list[list[object]] | list[object], debug=True,
              raise_if_exist=False, update_key=None):  #
    """ columns_order's names have to be the field name and not the column name. |columns_order|=|values|
    faire bien attention aux types, un cas ou un (int/float pk id) diffère de la variable et de l'input db, transformation en char de l'id pour résoudre le pb"""
    if type(values[0]) != list:
        values = [values]
    db_columns = get_columns_name_model(model)
    indexes_to_ignore = [columns_order.index(index) for index in set(columns_order) - set(db_columns)]
    columns_order = [column for column in columns_order if column in db_columns]
    rows = [dict(zip(columns_order, [value[i] for i in range(len(value)) if i not in indexes_to_ignore])) for value in values]
    try:
        if update_key:
            for record in rows:
                update_conditions = [getattr(model, key) == record[key] for key in
                                     (update_key if is_iter_but_not_str(update_key) else [update_key])]
                final_condition = update_conditions[0]
                for condition in update_conditions[1:]:
                    final_condition &= condition
                model.update(**record).where(final_condition).execute()
        else:
            model.insert_many(rows).execute()
    except Exception as e:  # todo peewee.OperationalError: database is locked
        print(traceback.format_exc(), "database may be locked sleep(1) & retry function")
        # if "order_id" in rows[0]:
        #     rows[0]["order_id"] += 0.1
        sleep(1)
        return fill_rows(model, columns_order, list(rows[0].values()), debug, True)
    #     if raise_if_exist:
    #         traceback.format_exc()
    #         raise IntegrityError
    #     else:
    #         return
    if debug:
        printc("{} rows filled {}".format(now(), values), color="black")
