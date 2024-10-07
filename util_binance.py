from collections import OrderedDict
from datetime import datetime, timedelta
from decimal import Decimal, getcontext
from http.client import RemoteDisconnected
import math
from operator import xor
import sys
from time import sleep
import traceback
from typing import Optional, TypeVar

from binance.enums import KLINE_INTERVAL_1WEEK
from binance.exceptions import BinanceAPIException
from openpyxl.workbook import Workbook
import requests
from requests import ReadTimeout
from urllib3.exceptions import ProtocolError

from Alert import say
from Candle import get_candles_data
from Colors import printc
from Files import run_file
from Jsons import json_base_to_json_ok
from OpenPyXL import cells_style
from Orders import DB
from Strings import float_to_spacefloat
from Times import now
from Util import sorted_dict
# from env import CLIENT, RESOURCES_PATH, WEIGHT

T = TypeVar("T")
E = TypeVar("E")
stable_coins = ["FDUSD", "USDT", "USDC"]
# bollinger_bets = ["1/4", "2/3", "1", "4/3", "7/4", "2/1", "5/2"]
# bollinger_bets = ["1/2", "3/4", "1", "5/4", "3/2"]
bollinger_bets = ["0", "0", "1", "2/1", "0"]


# pair: {Asset}
# devise: {quoteAsset}
# token: {baseAsset, crypto}
# actif: {devise & token}

# Decorators

def solve_binance_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (requests.exceptions.ConnectionError, RemoteDisconnected, ProtocolError, ReadTimeout):
            printc("ConnectionError", color="red")
            sleep(2)
            return solve_binance_errors(func)
        except BinanceAPIException as err:
            printc("Error {}°".format(err.code), color="red")
            if err.code == -1021:
                run_file(
                    r"B:\_Documents\Pycharm\Binance\errors_solver\Timestamp for this request is outside of the recvWindow.cmd")
                sleep(1)
                return func(*args, **kwargs)
            elif err.code == -2015:  # APIError(code=-2015): Invalid API-key, IP, or permissions for action.
                print(traceback.format_exc(), file=sys.stderr)
                exit()
            elif err.code == -2010:
                # Account has insufficient balance for requested action.
                sleep(0.1)
                return func(*args, **kwargs)
            else:
                print(traceback.format_exc(), file=sys.stderr)

    return wrapper


# Maths

def stepsize_to_precision(stepsize):
    return int(round(-math.log(stepsize, 10), 0))


def precision_to_stepsize(precision):
    return 10 ** -precision


def stepsizes_to_precision(*stepsizes):
    return list(map(stepsize_to_precision, stepsizes))


def precisions_to_stepsize(*precisions):
    return list(map(precision_to_stepsize, precisions))


def float_stepsize(value: float | str, stepsize: float) -> float:
    """
    >>> n = 5.123
    >>> [float_stepsize(n, 1), float_stepsize(n, 0.1), float_stepsize(n, 0.01)]
    [5.0, 5.1, 5.12]
    """
    return round(float(value), stepsizes_to_precision(stepsize)[0])


def float_to_str_rounded(value, decimal=8) -> str:
    """
    >>> n = 5.123
    >>> [float_to_str_rounded(n), float_to_str_rounded(n, 0), float_to_str_rounded(n, 1), float_to_str_rounded(n, 2)]
    ['5.12300000', '5', '5.1', '5.12']
    """
    decimal = "." + str(decimal) + "f"
    return "{:{}}".format(float(value), decimal)


def last_decimal_position(number: float) -> tuple[float, int]:
    """ Retourne un doublet contenant le step et la position de la dernière décimale d'un nombre
    >>> last_decimal_position(5.123))
    (0.001, 3)
    >>> print(last_decimal_position(52)
    (1.0, 0)
    """
    count_decimal = abs(Decimal(str(number)).as_tuple().exponent)
    return 1 / (10 ** count_decimal), count_decimal


def percent(current: float, fixe: float, r=2) -> float:
    return round((current / fixe - 1) * 100, r)


def add_percent(n, p, r=None):
    if r:
        return round((p / 100 + 1) * n, r)
    return (p / 100 + 1) * n


def binance_timestamp_to_datetime(timestamp: int):
    return datetime.fromtimestamp(timestamp / 1000)


def bets_strategy_double(bankroll=None, first_bet=None, max_try=None, last_trade_ratio=1, incr_bets=True):
    if not bankroll and not first_bet:
        bankroll = get_asset_quantity("BTC")
    max_try -= 1
    if bankroll is None:
        bankroll = first_bet * (2 ** max_try)
    elif first_bet is None:
        first_bet = bankroll / (2 ** max_try)
    last_try = (first_bet * 2 ** (max_try - 1))
    split_bet_for_incr = last_try * (1 - last_trade_ratio)
    next_start = bankroll + split_bet_for_incr * 2
    # print(first_try, start, last_try, split_bet_for_incr, next_start)
    if incr_bets is True:
        return bets_strategy_double(bankroll=next_start, max_try=max_try + 1, last_trade_ratio=last_trade_ratio,
                                    incr_bets=bankroll)
    else:
        if incr_bets is False:
            return [first_bet] + [first_bet * 2 ** i for i in range(max_try)]
        else:
            return [first_bet] + [first_bet * 2 ** i for i in range(max_try - 1)] + [incr_bets - last_try]


# All exchange

def pair_to_devise_token(pair, all_devises=None) -> tuple[str, str]:
    pair = pair.upper()
    if all_devises is None:
        all_devises = get_all_devises()
    devise, token = None, None
    for devise in all_devises:
        if devise == pair[len(pair) - len(devise):]:
            token = pair[:-len(devise)]
            break
    return token, devise


def is_pair(pair_or_actif, all_devises=None):
    return pair_to_devise_token(pair_or_actif, all_devises).count("") == 0


def actif_to_usd_pair(asset, all_pair=None) -> Optional[str]:
    asset = asset.upper()
    if all_pair is None:
        all_pair = get_all_pair_alive()
    for stable_coin in stable_coins:
        for pair in [asset + stable_coin, stable_coin + asset]:
            if pair in all_pair:
                return pair
    return None


def is_usd(devise):
    return "USD" in devise


# Account

# def bank_account(account=None) -> dict[str, dict]:  # 0, 10
#     """
#     >>> bank_account()
#     '{"WIN":{"asset":"WIN","free":50254.36800000,"locked":0.00000000},"HOT":{"asset":"HOT","free":2729.12200000,"locked":0.00000000}, ...}'
#     """
#     if account is None:
#         WEIGHT.put(10)
#         account = json_to_improve_dict(CLIENT.get_account()["balances"], key="asset")
#     return account

@solve_binance_errors
def get_asset_quantity(currency, r=None, account=None, free=True, locked=True):  # 0, 10
    """ Retourne la quantité d'une crypto libre à la décimal près."""
    if account is None:
        WEIGHT.put(10)
        balances = CLIENT.get_account()["balances"]
        account = json_base_to_json_ok(balances, ["asset"])
    tokens = 0
    if free:
        tokens += float(account[currency]["free"])
    if locked:
        tokens += float(account[currency]["locked"])
    return round(tokens, r) if r else tokens


# Market

@solve_binance_errors
def get_current_pairs_price(pair=None, offer=True) -> dict[str, dict[str, str]]:  # 1 2
    """ Retourne les prix actuel de toutes les paires.
    >>> get_current_pairs_price()
    {'ETHBTC': {'symbol': 'ETHBTC', 'bidPrice': '0.03165600', 'bidQty': '3.86000000', 'askPrice': '0.03165700', 'askQty': '19.10000000'}, ... }
    >>> get_current_pairs_price(pair="BTCFDUSD")
    {'BTCFDUSD': {'symbol': 'BTCFDUSD', 'bidPrice': '16589.14000000', 'bidQty': '0.01314000', 'askPrice': '16591.09000000', 'askQty': '0.00916000'}}
    >>> get_current_pairs_price(pair="BTCFDUSD", offer=False)
    {'BTCFDUSD': {'symbol': 'BTCFDUSD', 'price': '16583.99000000'}}
    """
    WEIGHT.put(2) if pair is None else WEIGHT.put(1)
    prices = CLIENT.get_orderbook_ticker(symbol=pair) if offer else CLIENT.get_symbol_ticker(symbol=pair)
    # requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='api.binance.com', port=443): Read timed out. (read timeout=10)
    return json_base_to_json_ok(prices, ["symbol"])


def get_current_pair_bid_price(pair) -> float:  # 1 2
    """ Current price of a pair"""
    try:
        return float(get_current_pairs_price(pair=pair)[pair]["bidPrice"])
    except TypeError as err:
        # print(traceback.format_exc(), file=sys.stderr)
        sleep(1)
        return get_current_pair_bid_price(pair)


def get_current_pair_ask_price(pair) -> float:  # 1 2
    """ Current price of a pair"""
    return float(get_current_pairs_price(pair=pair)[pair]["askPrice"])


def get_pair_price(pair, date: Optional[datetime] = None, wait=False) -> float:  # 1 2
    if date is None:
        return get_current_pair_bid_price(pair)
    df = get_candles_data(pair,
                          interval="1s",
                          start_timer=date,
                          end_timer=date,
                          debug=False)
    if len(df) == 0:
        if wait:
            sleep(1)
            return get_pair_price(pair, date, wait)
        return None
    return float(df.iloc[0]["close"])


def get_usd_price(asset, all_pair=None):
    if all_pair is None:
        all_pair = get_all_pair_alive()
    return get_current_pair_bid_price(actif_to_usd_pair(asset, all_pair))


@solve_binance_errors
def buy_market(pair, token_quantity=None, sound=False, devise_quantity=None, devise_stepsize=None, blocking=None,
               token_stepsize=None, emulate=None):
    """ same results as buy_market """
    if sound:
        say("MARKET BUY " + pair)
    if devise_stepsize is None or token_stepsize is None:
        devise_stepsize, token_stepsize = get_stepsize(pair)
    devise_precision = stepsize_to_precision(devise_stepsize)
    token_precision = stepsize_to_precision(token_stepsize)
    if emulate:
        if devise_quantity is not None:
            token_quantity = round((devise_quantity * 0.9999) / emulate["price"], token_precision)
        printc("MARKET BUY {0} {1} {2} {3}⏇ {4:.{5}f}Ð".format(binance_timestamp_to_datetime(emulate["transactTime"]),
                                                               pair, emulate["price"], token_quantity,
                                                               emulate["price"] * token_quantity,
                                                               devise_precision), color="black",
               background_color="green")
        return {"symbol": pair, "orderId": emulate["orderId"], "orderListId": "", "_clientOrderId": "",
                "transactTime": emulate["transactTime"], "price": emulate["price"], "origQty": "",
                "executedQty": token_quantity, "cummulativeQuoteQty": devise_quantity, "status": "FILLED",
                "timeInForce": emulate["transactTime"], "type": "MARKET", "side": "BUY",
                "workingTime": emulate["transactTime"], "fills": "", "selfTradePreventionMode": ""}
    price = round(get_current_pair_ask_price(pair) - devise_stepsize, devise_precision)
    if devise_quantity is not None and token_quantity is None:
        token_quantity = round((devise_quantity * 0.9999) / price, token_precision)
    token_quantity = round(token_quantity, token_precision)
    printc("MARKET BUY {0} {1} {2} {3}⏇ {4:.{5}f}Ð".format(now(), pair, price, token_quantity, price * token_quantity,
                                                           devise_precision), color="black", background_color="green")
    order = CLIENT.order_market_buy(symbol=pair, quantity=token_quantity)
    if not order:
        return
    if blocking:
        while order["status"] not in ["FILLED", "CANCELED"]:
            order = get_order(pair, order["orderId"])
            sleep(0.5)
    return order


@solve_binance_errors
def sell_market(pair, token_quantity=None, sound=False, devise_quantity=None, devise_stepsize=None, blocking=None,
                token_stepsize=None, emulate: dict = None):
    """ same results as buy_market """
    if sound:
        say("MARKET SELL " + pair)
    if devise_stepsize is None or token_stepsize is None:
        devise_stepsize, token_stepsize = get_stepsize(pair)
    devise_precision = stepsize_to_precision(devise_stepsize)
    token_precision = stepsize_to_precision(token_stepsize)
    if emulate:
        if devise_quantity is not None:
            token_quantity = (devise_quantity * 0.9999) / emulate["price"]
        token_quantity = round(token_quantity, token_precision)
        printc("MARKET SELL {0} {1} {2} {3}⏇ {4:.{5}f}Ð".format(binance_timestamp_to_datetime(emulate["transactTime"]),
                                                                pair, emulate["price"], token_quantity,
                                                                emulate["price"] * token_quantity,
                                                                devise_precision), color="black",
               background_color="red")
        return {"symbol": pair, "orderId": emulate["orderId"], "orderListId": "", "_clientOrderId": "",
                "transactTime": emulate["transactTime"], "price": emulate["price"], "origQty": "",
                "executedQty": token_quantity, "cummulativeQuoteQty": devise_quantity, "status": "FILLED",
                "timeInForce": emulate["transactTime"], "type": "MARKET", "side": "SELL",
                "workingTime": emulate["transactTime"], "fills": "", "selfTradePreventionMode": ""}
    price = round(get_current_pair_ask_price(pair) - devise_stepsize, devise_precision)
    if devise_quantity is not None and token_quantity is None:
        token_quantity = round((devise_quantity * 0.9999) / price, token_precision)
    token_quantity = round(token_quantity, token_precision)
    printc("MARKET SELL {0} {1} {2} {3}⏇ {4:.{5}f}Ð".format(now(), pair, price, token_quantity, price * token_quantity,
                                                            devise_precision), color="black", background_color="red")
    order = CLIENT.order_market_sell(symbol=pair, quantity=token_quantity)
    if not order:
        return
    if blocking:
        while order["status"] not in ["FILLED", "CANCELED"]:
            order = get_order(pair, order["orderId"])
            sleep(0.5)
    return order


@solve_binance_errors
def sell_limit(pair, price, token_quantity=None, devise_quantity=None, devise_stepsize=None, token_stepsize=None,
               sound=False) -> int:  # 1
    """ Results
    {'symbol': 'BTCFDUSD', 'orderId': 8269426031, 'orderListId': -1, 'clientOrderId': 'ru4Zs9tl8S0Ie46DXdKGWu', 'transactTime': 1674210485957, 'price': '20000.00000000', 'origQty': '0.01000000', 'executedQty': '0.00000000', 'cummulativeQuoteQty': '0.00000000', 'status': 'NEW', 'timeInForce': 'GTC', 'type': 'LIMIT', 'side': 'BUY', 'workingTime': 1674210485957, 'fills': [], 'selfTradePreventionMode': 'NONE'}
    """
    if sound:
        say("LIMIT SELL " + pair)
    if devise_stepsize is None or token_stepsize is None:
        devise_stepsize, token_stepsize = get_stepsize(pair)
    devise_precision = stepsize_to_precision(devise_stepsize)
    token_precision = stepsize_to_precision(token_stepsize)
    price = round(price, devise_precision) if devise_precision else price
    if devise_quantity is not None and token_quantity is None:
        token_quantity = round((devise_quantity * 0.9999) / price, token_precision)
    token_quantity = round(token_quantity, token_precision)
    # printc("LIMIT SELL {0} {1} {2} {3} {4:.{5}f}".format(now(), pair, price, token_quantity, price * token_quantity, devise_precision),
    #        color="red", background_color="white")
    print("LIMIT SELL {0} {1} {2} {3} {4:.{5}f}".format(now(), pair, price, token_quantity, price * token_quantity,
                                                        devise_precision))
    return CLIENT.order_limit_sell(symbol=pair, price=price, quantity=token_quantity)


@solve_binance_errors
def buy_limit(pair, price, token_quantity=None, devise_quantity=None, devise_stepsize=None, token_stepsize=None,
              sound=False) -> int:  # 1
    """ Results
    {'symbol': 'BTCFDUSD', 'orderId': 8269426031, 'orderListId': -1, 'clientOrderId': 'ru4Zs9tl8S0Ie46DXdKGWu', 'transactTime': 1674210485957, 'price': '20000.00000000', 'origQty': '0.01000000', 'executedQty': '0.00000000', 'cummulativeQuoteQty': '0.00000000', 'status': 'NEW', 'timeInForce': 'GTC', 'type': 'LIMIT', 'side': 'BUY', 'workingTime': 1674210485957, 'fills': [], 'selfTradePreventionMode': 'NONE'}
    """
    if sound:
        say("LIMIT BUY " + pair)
    if devise_stepsize is None or token_stepsize is None:
        devise_stepsize, token_stepsize = get_stepsize(pair)
    devise_precision = stepsize_to_precision(devise_stepsize)
    token_precision = stepsize_to_precision(token_stepsize)
    price = round(price, devise_precision) if devise_precision else price
    if devise_quantity is not None and token_quantity is None:
        token_quantity = round((devise_quantity * 0.9999) / price, token_precision)
    token_quantity = round(token_quantity, token_precision)
    # printc("LIMIT BUY {0} {1} {2} {3} {4:.{5}f}".format(now(), pair, price, token_quantity, price * token_quantity,
    #                                                     devise_precision), color="green", background_color="white")
    print("LIMIT BUY {0} {1} {2} {3} {4:.{5}f}".format(now(), pair, price, token_quantity, price * token_quantity,
                                                       devise_precision))
    return CLIENT.order_limit_buy(symbol=pair, price=price, quantity=token_quantity)


@solve_binance_errors
def sell_optimized(pair, token_quantity=None, devise_quantity=None, token_stepsize=None, devise_stepsize=None,
                   price=None, sound=False, blocking=False) -> int:  # 1
    """ Results
    {'symbol': 'BTCFDUSD', 'orderId': 8269426031, 'orderListId': -1, 'clientOrderId': 'ru4Zs9tl8S0Ie46DXdKGWu', 'transactTime': 1674210485957, 'price': '20000.00000000', 'origQty': '0.01000000', 'executedQty': '0.00000000', 'cummulativeQuoteQty': '0.00000000', 'status': 'NEW', 'timeInForce': 'GTC', 'type': 'LIMIT', 'side': 'BUY', 'workingTime': 1674210485957, 'fills': [], 'selfTradePreventionMode': 'NONE'}
    """
    if sound:
        say("OPTIMIZED SELL " + pair)
    if devise_stepsize is None or token_stepsize is None:
        devise_stepsize, token_stepsize = get_stepsize(pair)
    devise_precision = stepsize_to_precision(devise_stepsize)
    token_precision = stepsize_to_precision(token_stepsize)
    price = round(price if price is not None else get_current_pair_ask_price(pair) - devise_stepsize, devise_precision)
    if devise_quantity is not None and token_quantity is None:
        token_quantity = round((devise_quantity * 0.9999) / price, token_precision)
    token_quantity = round(token_quantity, token_precision)
    printc("OPTIMIZED SELL {0} {1} {2} {3} {4:.{5}f}".format(now(), pair, price, token_quantity, price * token_quantity,
                                                             devise_precision), color="black",
           background_color="cyan")
    order = None
    try:
        order = CLIENT.order_limit_sell(symbol=pair, quantity=token_quantity, price=price)
    except BinanceAPIException as err:
        printc("Account has insufficient balance for requested action", color="red")
        # if err.code == -2010:
        sleep(1)
        #     return buy_optimized(pair, token_quantity=token_quantity - token_stepsize, token_stepsize=token_stepsize,
        #                          devise_stepsize=devise_stepsize, sound=sound, is_long=is_long, blocking=blocking)
    if not order:
        return
    if blocking:
        while order["status"] not in ["FILLED", "CANCELED"]:
            order = get_order(pair, order["orderId"])
            sleep(0.5)
    return order["orderId"]


@solve_binance_errors
def buy_optimized(pair, token_quantity=None, devise_quantity=None, token_stepsize=None, devise_stepsize=None,
                  price=None, sound=False, blocking=False) -> int:  # 1
    """ Results
    {'symbol': 'BTCFDUSD', 'orderId': 8269426031, 'orderListId': -1, 'clientOrderId': 'ru4Zs9tl8S0Ie46DXdKGWu', 'transactTime': 1674210485957, 'price': '20000.00000000', 'origQty': '0.01000000', 'executedQty': '0.00000000', 'cummulativeQuoteQty': '0.00000000', 'status': 'NEW', 'timeInForce': 'GTC', 'type': 'LIMIT', 'side': 'BUY', 'workingTime': 1674210485957, 'fills': [], 'selfTradePreventionMode': 'NONE'}
    """
    if sound:
        say("OPTIMIZED BUY " + pair)
    if devise_stepsize is None or token_stepsize is None:
        devise_stepsize, token_stepsize = get_stepsize(pair)
    devise_precision = stepsize_to_precision(devise_stepsize)
    token_precision = stepsize_to_precision(token_stepsize)
    price = round(price if price is not None else get_current_pair_ask_price(pair) - devise_stepsize, devise_precision)
    if devise_quantity is not None and token_quantity is None:
        token_quantity = round((devise_quantity * 0.9999) / price, token_precision)
    token_quantity = round(token_quantity, token_precision)
    printc("OPTIMIZED BUY {0} {1} {2} {3} {4:.{5}f}".format(now(), pair, price, token_quantity, price * token_quantity,
                                                            devise_precision), color="black", background_color="cyan")
    order = None
    try:
        order = CLIENT.order_limit_buy(symbol=pair, price=price, quantity=token_quantity)
    except BinanceAPIException as err:
        printc("Account has insufficient balance for requested action", color="red")
        # if err.code == -2010:
        sleep(1)
        #     return buy_optimized(pair, token_quantity=token_quantity - token_stepsize, token_stepsize=token_stepsize,
        #                          devise_stepsize=devise_stepsize, sound=sound, is_long=is_long, blocking=blocking)
    if not order:
        return
    if blocking:
        while order["status"] not in ["FILLED", "CANCELED"]:
            order = get_order(pair, order["orderId"])
            sleep(0.5)
    return order["orderId"]


# binance.exceptions.BinanceAPIException: APIError(code=-2010): Account has insufficient balance for requested action.


@solve_binance_errors
def cancel_order(pair, order_id: int) -> dict:  # 1
    """ {'symbol': 'BTCFDUSD', 'origClientOrderId': '7jZNzSYl3VjLQvr9tuDITA', 'orderId': 8269689615, 'orderListId': -1, 'clientOrderId': 'f9EdG8vRp33V44MheZRVx9', 'price': '20000.00000000', 'origQty': '0.01000000', 'executedQty': '0.00000000', 'cummulativeQuoteQty': '0.00000000', 'status': 'CANCELED', 'timeInForce': 'GTC', 'type': 'LIMIT', 'side': 'BUY', 'selfTradePreventionMode': 'NONE'} """
    if type(order_id) is not int:
        return None
    try:
        return CLIENT.cancel_order(symbol=pair, orderId=order_id)
    except BinanceAPIException as err:
        if err.code == -2011:  # APIError(code=-2011): Unknown order sent.
            return None
        print(traceback.format_exc(), file=sys.stderr)


@solve_binance_errors
def update_order(pair, order_id, devise=None, token=None) -> dict:  # 1
    """ {'symbol': 'BTCFDUSD', 'origClientOrderId': '7jZNzSYl3VjLQvr9tuDITA', 'orderId': 8269689615, 'orderListId': -1, 'clientOrderId': 'f9EdG8vRp33V44MheZRVx9', 'price': '20000.00000000', 'origQty': '0.01000000', 'executedQty': '0.00000000', 'cummulativeQuoteQty': '0.00000000', 'status': 'CANCELED', 'timeInForce': 'GTC', 'type': 'LIMIT', 'side': 'BUY', 'selfTradePreventionMode': 'NONE'} """
    assert xor(devise, token)
    return CLIENT.cancel_order(symbol=pair, orderId=order_id)


@solve_binance_errors
def get_order(pair, order_id: int) -> dict:  # 2
    """ {'symbol': 'BTCFDUSD', 'origClientOrderId': '7jZNzSYl3VjLQvr9tuDITA', 'orderId': 8269689615, 'orderListId': -1, 'clientOrderId': 'f9EdG8vRp33V44MheZRVx9', 'price': '20000.00000000', 'origQty': '0.01000000', 'executedQty': '0.00000000', 'cummulativeQuoteQty': '0.00000000', 'status': 'CANCELED', 'timeInForce': 'GTC', 'type': 'LIMIT', 'side': 'BUY', 'selfTradePreventionMode': 'NONE'} """
    if type(order_id) is not int:
        return None
    return CLIENT.get_order(symbol=pair, orderId=order_id)


@solve_binance_errors
def is_new_order(pair, order_id: int) -> bool:  # 2
    """ {'symbol': 'BTCFDUSD', 'origClientOrderId': '7jZNzSYl3VjLQvr9tuDITA', 'orderId': 8269689615, 'orderListId': -1, 'clientOrderId': 'f9EdG8vRp33V44MheZRVx9', 'price': '20000.00000000', 'origQty': '0.01000000', 'executedQty': '0.00000000', 'cummulativeQuoteQty': '0.00000000', 'status': 'CANCELED', 'timeInForce': 'GTC', 'type': 'LIMIT', 'side': 'BUY', 'selfTradePreventionMode': 'NONE'} """
    if type(order_id) is not int:
        return False
    return get_order(symbol=pair, orderId=order_id)["status"] == "NEW"


@solve_binance_errors
def is_filled_order(pair, order_id) -> bool:  # 2
    """ {'symbol': 'BTCFDUSD', 'origClientOrderId': '7jZNzSYl3VjLQvr9tuDITA', 'orderId': 8269689615, 'orderListId': -1, 'clientOrderId': 'f9EdG8vRp33V44MheZRVx9', 'price': '20000.00000000', 'origQty': '0.01000000', 'executedQty': '0.00000000', 'cummulativeQuoteQty': '0.00000000', 'status': 'CANCELED', 'timeInForce': 'GTC', 'type': 'LIMIT', 'side': 'BUY', 'selfTradePreventionMode': 'NONE'} """
    return get_order(symbol=pair, orderId=order_id)["status"] == "FILLED"


@solve_binance_errors
def is_cancel_order(pair, order_id) -> bool:  # 2
    """ {'symbol': 'BTCFDUSD', 'origClientOrderId': '7jZNzSYl3VjLQvr9tuDITA', 'orderId': 8269689615, 'orderListId': -1, 'clientOrderId': 'f9EdG8vRp33V44MheZRVx9', 'price': '20000.00000000', 'origQty': '0.01000000', 'executedQty': '0.00000000', 'cummulativeQuoteQty': '0.00000000', 'status': 'CANCELED', 'timeInForce': 'GTC', 'type': 'LIMIT', 'side': 'BUY', 'selfTradePreventionMode': 'NONE'} """
    return get_order(symbol=pair, orderId=order_id)["status"] == "CANCELED"


@solve_binance_errors
def get_all_open_orders(pair=None) -> dict:  # 3, 40
    """ {8270484375: {'symbol': 'BTCFDUSD', 'orderId': 8270484375, 'orderListId': -1, 'clientOrderId': 'EjjcVWqUa2cFDNeGiRAAnJ', 'price': '20000.00000000', 'origQty': '0.01000000', 'executedQty': '0.00000000', 'cummulativeQuoteQty': '0.00000000', 'status': 'NEW', 'timeInForce': 'GTC', 'type': 'LIMIT', 'side': 'BUY', 'stopPrice': '0.00000000', 'icebergQty': '0.00000000', 'time': 1674215735899, 'updateTime': 1674215735899, 'isWorking': True, 'workingTime': 1674215735899, 'origQuoteOrderQty': '0.00000000', 'selfTradePreventionMode': 'NONE'}, ...} """
    if pair is None:
        return CLIENT.get_open_orders()
    return json_base_to_json_ok(CLIENT.get_open_orders(symbol=pair), ["orderId"])


@solve_binance_errors
def is_end_order(pair, order_id) -> bool:  # 2
    """ {'symbol': 'BTCFDUSD', 'origClientOrderId': '7jZNzSYl3VjLQvr9tuDITA', 'orderId': 8269689615, 'orderListId': -1, 'clientOrderId': 'f9EdG8vRp33V44MheZRVx9', 'price': '20000.00000000', 'origQty': '0.01000000', 'executedQty': '0.00000000', 'cummulativeQuoteQty': '0.00000000', 'status': 'CANCELED', 'timeInForce': 'GTC', 'type': 'LIMIT', 'side': 'BUY', 'selfTradePreventionMode': 'NONE'} """
    return get_order(symbol=pair, orderId=order_id)["status"] in ["FILLED", "CANCELED"]
    # return order_id in get_all_open_orders(pair)


@solve_binance_errors
def all_orders(pair: str, start_time=None):  # 10
    """ Retourne toutes les ordres qui ont été effectée sur une pair.
    >>> all_orders("BNFDUSDT")
    {"354.69000000":{"clientOrderId":"ios_301e60dd0a804b279819e30bbe771b97","cummulativeQuoteQty":875.90380200,"executedQty":2.46970000,"icebergQty":0.00000000,"isWorking":"True","orderId":"2493901119","orderListId":-1,"origQty":2.46970000,"origQuoteOrderQty":0.00000000,"price":354.69000000,"side":"BUY","status":"FILLED","stopPrice":0.00000000,"symbol":"BNFDUSDT","time":"1624004384120","timeInForce":"GTC","type":"LIMIT","updateTime":"1624004384120"}, "471.97930000":{"clientOrderId":"ios_da658e11b4f04bbb8d43f28188cff965","cummulativeQuoteQty":32.09459240,"executedQty":0.06800000,"icebergQty":0.00000000,"isWorking":"True","orderId":"1942052560","orderListId":-1,"origQty":0.06800000,"origQuoteOrderQty":0.00000000,"price":471.97930000,"side":"BUY","status":"FILLED","stopPrice":0.00000000,"symbol":"BNFDUSDT","time":"1618781984342","timeInForce":"GTC","type":"LIMIT","updateTime":"1618781999309"}, ... }
    """
    WEIGHT.put(10)
    orders = CLIENT.get_all_orders(symbol=pair, startTime=int(start_time.timestamp() * 1000))
    items = list(json_base_to_json_ok(orders, ["updateTime"] if "updateTime" in orders else ["time"]).items())
    return OrderedDict({binance_timestamp_to_datetime(k): v for (k, v) in items})


def kline_to_meaning_dict(kline):
    kline = [float(value) if type(value) is str else value for value in kline]
    columns = "time", "open", "high", "low", "close", "volume", "close_time", "devise_volume", "trades", "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "can_be_ignored"
    d = dict(zip(columns, kline))
    getcontext().prec = len(str(d["open"]))
    d["time"] = str(binance_timestamp_to_datetime(d["time"]))
    d["close_time"] = str(binance_timestamp_to_datetime(d["close_time"]))
    return d


def is_new_limit_order(order):
    return float(order["executedQty"]) == 0


# noinspection PyPep8Naming
def order_to_meaning_dict(order):
    fills, transactTime, time, updateTime = [None] * 4
    if len(order) == 16:
        """ exexcuting [market order] """
        symbol, orderId, orderListId, _clientOrderId, transactTime, price, origQty, executedQty, cummulativeQuoteQty, \
            status, timeInForce, _type, side, workingTime, fills, selfTradePreventionMode = order.values()
    elif len(order) == 20:
        """ existing [market order / limit order] """
        symbol, orderId, orderListId, clientOrderId, price, origQty, executedQty, cummulativeQuoteQty, status, \
            timeInForce, _type, side, stopPrice, icebergQty, time, updateTime, isWorking, workingTime, origQuoteOrderQty, \
            selfTradePreventionMode = order.values()
    else:
        print(len(order), "order_to_meaning_dict", file=sys.stderr)
        raise ValueError

    if order["executedQty"] and float(order["executedQty"]) == 0 and order["status"] in ["CANCELED", "NEW"]:
        # Une order limit passe de NEW à CANCELED ou FILLED
        return "ignore"
    time = transactTime or time
    updateTime = updateTime or time
    executedQty = float(executedQty)
    sign = 1 if order["side"] == "BUY" else -1
    cummulativeQuoteQty = executedQty * price if cummulativeQuoteQty is None else cummulativeQuoteQty
    executedQty = cummulativeQuoteQty / price if executedQty is None else executedQty
    order_dict = {}
    order_dict.update({"status": status,
                       "side": side,
                       "time_created": binance_timestamp_to_datetime(time),
                       "time_executed": binance_timestamp_to_datetime(updateTime),
                       "pair": symbol,
                       "id": orderId,
                       "type": _type,
                       "sign": sign,
                       "token": sign * executedQty,
                       "devise": -sign * float(cummulativeQuoteQty),
                       })
    if _type == "MARKET":
        order_dict.update({"price": float(order["price"]) or (float(cummulativeQuoteQty) / executedQty)})
    elif "LIMIT" in _type:
        order_dict.update({"price": float(price),
                           "limit_token": float(origQty),
                           "limit_price": float(price),
                           })
    # trash = {"orderListId": orderListId, "clientOrderId": clientOrderId, "origQty": origQty, "timeInForce": timeInForce,
    #          "workingTime": workingTime, "selfTradePreventionMode": selfTradePreventionMode,
    #          "price": price}
    return order_dict


@solve_binance_errors
def get_candle(pair, interval, cursor_start_time=None):  # 1
    WEIGHT.put(1)
    if cursor_start_time is not None:
        datas = CLIENT.get_klines(symbol=pair, interval=interval, limit=1000,
                                  startTime=int(cursor_start_time.timestamp()) * 1000)
    else:
        datas = CLIENT.get_klines(symbol=pair, interval=interval, limit=1000)
    open_time, _open, high, low, close, volume, close_time, quote_asset_volume, trades, taker_buy_base_asset_volume, taker_buy_quote_asset_volume, _ = list(
        zip(*datas))
    datas = {
        "open_time": open_time,
        "open": _open,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "close_time": close_time,
        "quote_asset_volume": quote_asset_volume,
        "taker_buy_base_asset_volume": taker_buy_base_asset_volume,
        "taker_buy_quote_asset_volume": taker_buy_quote_asset_volume,
    }
    return datas


# Binance

def binance_ts_to_datetime(ts):
    return datetime.fromtimestamp(float(ts) / 1000)


@solve_binance_errors
def get_all_tokens_n_devises(force=False):  # ?
    """ v["status"] == BREAK si binance est en pause """
    devises_count = {}
    tokens_count = {}
    pairs = json_base_to_json_ok(CLIENT.get_exchange_info(), keys_aim=["symbol"], keys_path_to_start=["symbols"])
    for pair, v in pairs.items():
        if v["status"] != "TRADING" and not (force and v["status"] == "BREAK"):
            continue
        devise, token = v["quoteAsset"], v["baseAsset"]
        amount, devise_pair = devises_count.get(devise, (0, []))
        devises_count[devise] = amount + 1, devise_pair + [pair]
        amount, token_pair = tokens_count.get(token, (0, []))
        tokens_count[token] = amount + 1, token_pair + [pair]
    devises_count = sorted(devises_count.items(), key=lambda x: -x[1][0])
    tokens_count = sorted(tokens_count.items(), key=lambda x: -x[1][0])
    return tokens_count, devises_count


def get_all_devises(force=False):  # ?
    return list(map(lambda x: x[0], get_all_tokens_n_devises(force)[1]))


def get_all_tokens():  # ?
    return list(map(lambda x: x[0], get_all_tokens_n_devises()[0]))


def get_all_actifs():  # ?
    v = get_all_tokens_n_devises()
    return sorted(set(map(lambda x: x[0], v[0])).union(set(map(lambda x: x[0], v[1]))))


def get_ranked_pair_marketcap(*actifs, pairs_check="all", interval=KLINE_INTERVAL_1WEEK, fast=True) \
        -> list[tuple[str, str]]:  # 1, 40
    """
    >>> get_ranked_pair_marketcap("USD", "BTC", "ETH", "BNB", "EUR")
    """
    all_pairs = get_all_pair_alive() if pairs_check == "all" else pairs_check
    pairs_prices = get_current_pairs_price()
    all_devises = get_all_devises()
    volumes_usd: dict[str, str] = {}
    pairs = set(all_pairs).difference({"UPUSDT", "DOWNUSDT"})
    for pair in pairs:
        token, devise = pair_to_devise_token(pair, all_devises)
        if fast and token not in all_devises:
            continue
        for actif in actifs:
            if actif not in pair or pair in volumes_usd:
                continue
            volume = volume_to_usd_volume(pair, interval, pairs_prices, all_devises, pairs)
            if volume is None:
                continue
            pair_volume = float_to_spacefloat(int(volume))
            volumes_usd[pair] = pair_volume
    # noinspection PyTypeChecker
    return sorted(volumes_usd.items(), key=lambda x: -int(x[1].replace(" ", "")))


def volume_to_usd_volume(pair, interval, pairs_prices, all_devises, all_pairs) -> Optional[float]:
    volume = float(get_candle(pair, interval)["volume"][-1])
    token, devise = pair_to_devise_token(pair, all_devises)
    if is_usd(devise):
        price = float(pairs_prices[pair]["bidPrice"])
        return volume * price
    stable_pair = actif_to_usd_pair(token, all_pairs)
    if stable_pair is None:
        return None
    price = float(pairs_prices[stable_pair]["bidPrice"])
    volume_usd = volume * price
    return volume_usd


@solve_binance_errors
def get_all_pair_price_dead() -> dict[str, dict[str, str]]:  # 2
    """ Retourne les prix actuels de toutes les paires mortes de Binance. """
    WEIGHT.put(2)
    return {asset[0]: asset[1] for asset in
            json_base_to_json_ok(CLIENT.get_orderbook_ticker(), ["symbol"]).items() if
            asset[1]["bidPrice"] == "0.00000000" and asset[1]["bidQty"] == "0.00000000"}


@solve_binance_errors
def get_all_pair_price_alive(token=None) -> dict[str, dict[str, str]]:  # 2
    """ Retourne les prix actuels de toutes les paires actives sur le marché de Binance. """
    WEIGHT.put(2)
    return {asset[0]: asset[1] for asset in
            json_base_to_json_ok(CLIENT.get_orderbook_ticker(), ["symbol"]).items() if
            asset[1]["bidPrice"] != "0.00000000" and asset[1]["bidQty"] != "0.00000000" and (
                    token is None or token in asset[0])}


@solve_binance_errors
def get_all_pair_alive(token=None) -> list[str]:  # 2
    """ Retourne la liste de toutes les paires actives sur le marché de Binance.
    >>> get_all_pair_alive()
    ['1INCHBTC', '1INCHFDUSD', ...]
    """
    WEIGHT.put(2)
    return sorted(get_all_pair_price_alive(token))


@solve_binance_errors
def fee_pairs() -> dict:  # 1
    """ Retourne le dictionnaire contenant les frais des pairs, des petites aux plus grosses.
    >>> fee_pairs()
    {"1INCHFDUSD":{"makerCommission":"0","symbol":"1INCHFDUSD","takerCommission":0.001},"AAVEFDUSD":{"makerCommission":"0","symbol":"AAVEFDUSD","takerCommission":0.001}, ... }
    """
    WEIGHT.put(1)
    pair_fee_infos = json_base_to_json_ok(CLIENT.get_trade_fee(), ["symbol"])
    return sorted_dict(pair_fee_infos, key=lambda x: x[1]["makerCommission"])


def get_no_fee_pairs(maker: bool = True, taker: bool = False) -> dict:  # 1
    # noinspection PyUnresolvedReferences
    """
        >>> get_no_fee_pairs(maker=True, taker=True)
        >>> [{k: v} for (k, v) in get_no_fee_pairs().items() if "BTC" in k]
        >>> [k for (k, v) in get_no_fee_pairs().items() if "BTC" in k]
        """
    fees = fee_pairs()
    return {k: v for (k, v) in fees.items()
            if (not maker or maker and v["makerCommission"] == "0")
            and (not taker or taker and v["takerCommission"] == "0")}


@solve_binance_errors
def get_stepsize(pair: str) -> tuple[float, float]:  # 1
    """ Retourne le devise_stepsize autorisé par binance d'une crypto.
    >>> [get_stepsize("BNFDUSDT"), get_stepsize("ETHUSDT"), get_stepsize("BTCUSDT")]
    [(0.1, 0.001), (0.01, 0.0001), (0.01, 1e-05)]
    """
    WEIGHT.put(1)
    precisions = json_base_to_json_ok(CLIENT.get_symbol_info(pair)["filters"], ["filterType"])
    devise_stepsize, token_stepsize = map(float, [precisions["PRICE_FILTER"]["tickSize"],
                                                  precisions["LOT_SIZE"]["stepSize"]])
    return devise_stepsize, token_stepsize


@solve_binance_errors
def get_minimal_order_devise_amount(pair: str) -> float:  # 1
    WEIGHT.put(1)
    return float(json_base_to_json_ok(CLIENT.get_symbol_info(pair)["filters"],
                                      ["filterType"])["NOTIONAL"]["minNotional"])


def last_trades_to_excel(token, devise, start, fee=0.000650):
    pair = token + devise
    workbook: Workbook = Workbook()
    workbook.remove(workbook.active)
    sheet = workbook.create_sheet(pair)
    token_price = float(get_current_pairs_price(pair=token + "FDUSD")[token + "FDUSD"]["bidPrice"])
    devise_price = 1 if devise == "FDUSD" else float(
        get_current_pairs_price(pair=devise + "FDUSD")[devise + "FDUSD"]["bidPrice"])
    columns = ["pair", "date", "order", "side", "price", "token", "devise", "cash", "cash fee", "devise (with fee)"]
    sheet.append(columns)
    sum_price = 0
    sum_fee = 0
    token_gain = 0
    devise_gain = 0
    i = 0
    for (k, v) in list(all_orders(pair, start).items()):
        if v["status"] == "CANCELED" or v["status"] == "NEW":
            continue
        pair = pair
        date = binance_timestamp_to_datetime(v["time"])
        order = v["type"]
        side = v["side"]
        sign = 1 if side == "BUY" else -1
        token = float(v['executedQty'])
        devise = float(v['cummulativeQuoteQty'])
        devise_fee = devise * fee
        price = devise / token
        # columns = ["pair", "date", "order", "side", "price", "token", "devise", "cash", "cash fee", "devise (with fee)"]
        row = (pair, date, order, side, price, token, devise, devise * devise_price, devise_fee * devise_price,
               devise * devise_price - devise_fee * devise_price)
        sheet.append(row)
        sum_price += price
        sum_fee += devise_fee
        token_gain += sign * token
        devise_gain -= sign * devise
        i += 1
    last_row = (
        "", "", "", "", sum_price / i, token_gain, devise_gain, devise_gain * devise_price, sum_fee * devise_price,
        devise_gain * devise_price - sum_fee * devise_price + token_gain * token_price)
    sheet.append(last_row)
    cells_style(sheet)
    workbook.save(filename=RESOURCES_PATH + pair + ".xlsx")


def swap_token(asset_from, asset_to, asset_from_to_sell: Optional[float] = None,
               asset_from_quantity_to_buy: Optional[float] = None,
               asset_from_quantity_to_aim: Optional[float] = None):
    all_pair = get_all_pair_alive()
    all_devises = get_all_devises()
    if not asset_from_to_sell and not asset_from_quantity_to_buy and not asset_from_quantity_to_aim:
        asset_from_to_sell = get_asset_quantity(asset_from) * 0.9999
    if asset_from_quantity_to_aim:
        asset_from_quantity_to_buy = asset_from_quantity_to_aim - get_asset_quantity(asset_from)
        if asset_from_quantity_to_buy < 0:
            asset_from_to_sell = abs(asset_from_quantity_to_buy)
            asset_from_quantity_to_buy = None
    pair = actif_to_usd_pair(asset_to, all_pair)
    min_order = get_minimal_order_devise_amount(pair)
    token_name, devise_name = pair_to_devise_token(pair, all_devises)
    if asset_to == token_name:
        if asset_from_to_sell:
            if asset_from_to_sell <= min_order:
                sell_optimized(pair, devise_quantity=min_order * 1.1, blocking=True)
                asset_from_to_sell += min_order * 1.1
            buy_optimized(pair, devise_quantity=asset_from_to_sell, blocking=True)
        elif asset_from_quantity_to_buy:
            if asset_from_quantity_to_buy <= min_order:
                asset_from_quantity_to_buy += min_order * 1.1
                buy_optimized(pair, devise_quantity=min_order * 1.1, blocking=True)
            sell_optimized(pair, devise_quantity=asset_from_quantity_to_buy, blocking=True)
    elif asset_to == devise_name:
        if asset_from_to_sell <= min_order:
            asset_from_to_sell += min_order * 1.1
            buy_optimized(pair, devise_quantity=min_order * 1.1, blocking=True)
        sell_optimized(pair, devise_quantity=asset_from_to_sell, blocking=True)


def dataframe_to_pipescript():
    pipescript_text = """//@version=5
    indicator("My Trades", overlay=true)
    """.format()
    # DB.
    # plot(22200, color=color.red, linewidth=2, style=plot.style_circles, offset=0, show_last=1)
    # plot(22200, color=color.green, linewidth=2, style=plot.style_circles, offset=-2, show_last=1)


def interval_to_timedelta(interval):
    if "m" in interval:
        time_delta_interval = timedelta(minutes=int(interval[:interval.index("m")]))
        freq = "T"
    elif interval == "1s":  # todo per day instead per month
        time_delta_interval = timedelta(seconds=1)
        freq = "s"
    else:
        raise "interval problem"
    return time_delta_interval, freq


###
# to redo or delete
# def get_rank_top200(update=False) -> list[str]:
#     """ Return coins sorted by rank (market cap)"""
#     # "2fedac4f-7953-431c-a638-8d41538e28ed"
#     # "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
#     file_name = RESOURCES_PATH + "top200.csv"
#     if not update and file_exist(file_name):
#         return list(pd.read_csv(file_name, sep=";")["0"].values)
#     coinmarketcap_url = "https://coinmarketcap.com/all/views/all/"
#     browser = Browser(Point(0, -1080), headless=True)
#     browser.new_page(coinmarketcap_url)
#     coins = browser.get_element("/html/body/div[1]/div[1]/div[2]/div/div[1]/div/div[2]/div[3]/div/table/tbody")
#     coins_rank = []
#     # browser.wait_element_n_click(coinmarketcap_url, "/html/body/div[3]/div/div/div[2]/div/button")
#     rows = coins.find_elements_by_tag_name("tr")
#     for i in range(len(rows)):
#         if i % 20 == 0:
#             j = min(i + 20, len(rows) - 1)
#             browser.move_to(rows[j])
#         coin_text = get_element_text(rows[i])
#         if not coin_text or len(coin_text.split("\n")) < 5:
#             continue
#         rank, name, asset, market_cap, price, supply, volume, _, _, _ = coin_text.split("\n")
#         # coins_rank.append((asset, int(market_cap.replace(",", "").replace(" ", "").replace("$", ""))))
#         coins_rank.append(asset)
#         rows = coins.find_elements_by_tag_name("tr")
#     pd.Series(coins_rank).to_csv(file_name, sep=";")
#     return coins_rank
#
#
# def fill_csv_files(last_days=7, top_rank=100, update=False) -> None:
#     start = now() - timedelta(days=last_days)
#     top = get_rank_top200(update)[:top_rank]
#     for asset in top:
#         candles = get_candles_datas("{}FDUSD".format(asset), CLIENT.KLINE_INTERVAL_1MINUTE, start)
#         if candles is None or not len(candles):
#             get_candles_datas("{}USDT".format(asset), CLIENT.KLINE_INTERVAL_1MINUTE, start)
#         get_candles_datas("{}BTC".format(asset), CLIENT.KLINE_INTERVAL_1MINUTE, start)
#
#
# def get_coins_by_volatility(update=False, sample_length=180) -> DataFrame:
#     def add_row(df, pair):
#         filename = CANDLES_PATH + pair + "_1m.csv"
#         if file_exist(filename):
#             csv_asset = pd.read_csv(filename, sep=";")
#             csv_asset = csv_asset.loc[:, csv_asset.columns != "Unnamed: 0"][:sample_length]["volatility"]
#             volatility = csv_asset.mean()
#             df = add_rows_dataframe(df, {"rank": [i], "pair": [pair], "volatility": [volatility]})
#         return df
#
#     if update:
#         fill_csv_files(update=update)
#     top_200 = get_rank_top200()
#     df = DataFrame()
#     for i in range(len(top_200)):
#         asset = top_200[i]
#         df = add_row(df, asset + "FDUSD")
#         df = add_row(df, asset + "USDT")
#         df = add_row(df, asset + "BTC")
#     return df.sort_values("volatility", ascending=False)


# def complete_sell_order_pairs(pairs: Iterable[str], devise="USDT"):  # 5
#     """ A tester """
#     assets = list(map(lambda x: x.replace(devise, ""), pairs))
#     pair_prices: dict[str, dict[str, str]] = get_all_pair_price(CLIENT)
#     assets_infos = json_to_improve_dict(CLIENT.get_account()["balances"], key="asset")
#     for asset in assets:
#         pair = asset + devise
#         cash = asset_cash_estimation_free \
#             (asset, devise, True, pair_prices, assets_infos=assets_infos)
#         if cash >= 10.01:
#             devise_stepsize = get_stepsize(pair)
#             coins = float(assets_infos[asset]["free"])
#             ask = float(pair_prices[pair]["askPrice"])
#             bid = float(pair_prices[pair]["bidPrice"])
#             sell_order = float(float_decimal(ask, max(last_decimal_position(ask)[1], last_decimal_position(bid)[1])))
#             if "UP" in asset or "DOWN" in asset:
#                 print(asset)
#                 try:
#                     print("sell_limit", asset, coins, sell_order)
#                     sleep(1)
#                     order = CLIENT.order_limit_sell(symbol=pair, token_quantity=coins, price=sell_order)
#                     print("\nOK. order = ", order)
#                 except BinanceAPIException as binanceError:
#                     print("Message Error", binanceError.message, pair)
#                     coins = float_stepsize(coins - devise_stepsize, devise_stepsize)
#                     print("sell_limit_step", asset, coins, sell_order)
#                     order = CLIENT.order_limit_sell(symbol=pair, token_quantity=coins, price=sell_order)
#                     print("\nOK.order = ", order)
#
#
# def get_all_up_and_down_pairs():  # 2
#     all_up_n_down = [p for p in get_all_pair_name_alive() if "UP" in p or "DOWN" in p]
#     all_up_n_down.remove("SUPERBTC")
#     all_up_n_down.remove("SUPERFDUSD")
#     all_up_n_down.remove("SUPERUSDT")
#     return all_up_n_down
#
#
# def cancel_all_order_pairs(pairs: Iterable[str], order_side=None):
#     all_open_orders = all_open_orders_pairs()
#     for pair in pairs:
#         if pair in all_open_orders:
#             if order_side is not None:
#                 if all_open_orders[pair]["side"] == order_side:
#                     CLIENT.cancel_order(symbol=pair, orderId=all_open_orders[pair]["orderId"])
#             else:
#                 CLIENT.cancel_order(symbol=pair, orderId=all_open_orders[pair]["orderId"])
#
#

#
#
#
##
#
#
# def bank_account_str(account=None) -> str:  # 0, 10
#     """
#     >>> bank_account()
#     '{"WIN":{"asset":"WIN","free":50254.36800000,"locked":0.00000000},"HOT":{"asset":"HOT","free":2729.12200000,"locked":0.00000000}, ...}'
#     """
#     return sorted_dict(bank_account(account),
#                        key=lambda x: (1 / (float(x[1]["free"]) + 1), 1 / (float(x[1]["locked"]) + 1)))
#
#
# def asset_cash_estimation(asset_from: str, asset_to: str = "USDT", offer=True, pair_prices=None,
#                           assets_infos=None) -> float:  # 0, 10
#     if assets_infos is None:
#         WEIGHT.put(10)
#         assets_infos = json_to_improve_dict(CLIENT.get_account()["balances"], key="asset")
#     asset_infos = assets_infos[asset_from]
#     cash_estimation = float(asset_infos["free"]) + float(asset_infos["locked"])
#     if asset_from == asset_to:
#         return cash_estimation
#     pair = asset_infos["asset"] + asset_to
#     if pair not in pair_prices:
#         return 0
#     if offer:
#         value_price = float(pair_prices[pair]["bidPrice"])
#     else:
#         value_price = float(pair_prices[pair]["price"])
#     return cash_estimation * value_price
#
#
# def asset_cash_estimation_free(asset_from: str, asset_to: str = "USDT", offer=True, pair_prices=None,
#                                assets_infos=None) -> float:  # 0, 10
#     if assets_infos is None:
#         WEIGHT.put(10)
#         assets_infos = json_to_improve_dict(CLIENT.get_account()["balances"], key="asset")
#     asset_infos = assets_infos[asset_from]
#     cash_estimation = float(asset_infos["free"])
#     if asset_from == asset_to:
#         return cash_estimation
#     pair = asset_infos["asset"] + asset_to
#     if pair not in pair_prices:
#         return 0
#     if offer:
#         value_price = float(pair_prices[pair]["bidPrice"])
#     else:
#         value_price = float(pair_prices[pair]["price"])
#     return cash_estimation * value_price
#
#
# def launch_web_chart_commited_pair(other_way: list[str] = ()):
#     devise = "USDT"
#     start_url = "https://cryptowat.ch/fr-fr/charts/BINANCE:"
#     end_url = "?period=15m"
#     start_url_other_way = "https://www.binance.com/fr/trade/"
#     end_url_other_way = "?type=spot"
#     for asset in map(lambda x: x[0], bank_estimation()[1]):
#         if asset != devise:
#             if asset not in other_way:
#                 util_launch_web(start_url + asset + "-" + devise + end_url, "edge")
#             else:
#                 util_launch_web(start_url_other_way + asset + "_" + devise + end_url_other_way, "edge")
#         sleep(2)
#
#
# def bank_estimation(assets_infos=None, pair_prices=None, offer=True) -> tuple[
#     float, list[str, float], float]:  # 0, 10, 12
#     """ Retourne la valeur en dollars de la banque avec pour chacune des crypto dans le compte sa valeur en dollars et sa quantité.
#     >>> bank_estimation()
#     (4393.074714487893, [('FDUSD', (1261.79, 1262.16888759)), ... , 3694.142881338625)
#     """
#     print("in")
#     if assets_infos is None:
#         WEIGHT.put(10)
#         assets_infos = json_to_improve_dict(CLIENT.get_account()["balances"], key="asset")
#     if pair_prices is None:
#         WEIGHT.put(2)
#         pair_prices = get_all_pair_price(offer)
#     cash_bank = 0
#     assets_cash = {}
#     # not_pair = ["UP", "DOWN"]
#     not_pair = []
#     for asset_infos in assets_infos.values():
#         coins = float(asset_infos["free"]) + float(asset_infos["locked"])
#         cash = asset_cash_estimation(asset_infos["asset"], "USDT", offer=True, pair_prices=pair_prices,
#                                      assets_infos=assets_infos)
#         if cash < 1 and asset_infos["asset"] != "USDT" or asset_infos["asset"] in not_pair:
#             continue
#         cash_bank += cash
#         cash_visuel = float("{:.2f}".date_format(cash))
#         if cash_visuel > 0:
#             assets_cash[asset_infos["asset"]] = (cash_visuel, coins)
#     cash_bank_eur = cash_bank / float(pair_prices["EURUSDT"]["askPrice"])
#     return cash_bank, sorted(assets_cash.items(), key=lambda x: 1 / x[1][0]), cash_bank_eur
#
#
# def trade_max_value(ratio=1 / 20) -> float:
#     """ Retourne la valeur max accepté par un trade manuel. Fluctue en fonction des stables coins """
#     stables_devises = ["USDT", "FDUSD"]
#     return amount_asset_free(stables_devises) * ratio
#
#
# def amount_asset_free(assets: Union[Iterable[str], str] = "USDT", account=None,
#                       pair_prices=None) -> float:  # 0, 2, 10, 12
#     """ Retourne la quantité libre d'une ou de plusieurs crypto en USDT.
#     >>> amount_asset_free("USDT")
#     182.89298754
#     """
#     asset_infos = bank_account(account)
#     if pair_prices is None:
#         WEIGHT.put(2)
#         pair_prices = get_all_pair_price()
#     if not util_is_iterable(assets):
#         return asset_cash_estimation_free(assets, "USDT", pair_prices=pair_prices,
#                                           assets_infos=asset_infos)
#     else:
#         return sum([asset_cash_estimation_free(asset, "USDT", offer=True, pair_prices=pair_prices,
#                                                assets_infos=asset_infos) for asset in asset_infos
#                     if asset in assets])
#
#
# def parser_screener(pattern_start="data-symbol=\"BINANCE:", pattern_end="\">") -> list[str]:
#     """ Je ne sais plus """
#     names: list[str] = []
#     file = open("txt/parse_screener.txt", "r")
#     for line in file.readlines():
#         if line.find("data-field-key=") > 0:
#             start_name_index = line.find(pattern_start) + len(pattern_start)
#             end_name_index = line.find(pattern_end, start_name_index)
#             name: str = line[start_name_index:end_name_index]
#             if name[-4:] == "USDT" and name.find("DOWN") == -1 and name.find("UP") == -1:
#                 names.append(name)
#     file.close()
#     return names[:-1]
#
#
#
#
#
# def all_open_orders_pairs():  # 40
#     WEIGHT.put(40)
#     return json_to_improve_dict(CLIENT.get_open_orders(), key="symbol")
#
#
# def all_open_orders_pair(pair: str):  # 3
#     WEIGHT.put(3)
#     return json_to_improve_dict(CLIENT.get_open_orders(pair), key="symbol")
#
#
#
#
#
#
#
#
#
#
# def delete_log_file():  # supprime les anciens fichiers log
#     """ Je ne sais plus. """
#     for file_name in glob.glob("logs/*.txt"):
#         try:
#             os.remove(file_name)
#         except OSError as e:
#             print("Error: %s : %s" % (file_name, e.strerror))
#     # input("Voulez vous REINITIALISER ???")
#     # REINITIALISER = {pair: [open("historics/" + pair + ".txt", "w").close(), 0] for pair in pairs}
#
#
# def delete_trades_files():  # supprime les anciens fichiers py
#     """ Je ne sais plus. """
#     for file_name in glob.glob("trades/la/*.py"):
#         try:
#             os.remove(file_name)
#         except OSError as e:
#             print("Error: %s : %s" % (file_name, e.strerror))
#     file = open("trades/base_print.py", "r")
#     # file_pattern = "\n".join(file.readlines())
#     file.close()
#
#
# def copy_base_file_to_all_pair_file():
#     """ Je ne sais plus. """
#     file = open("trades/base.py", "r")
#     file_pattern = "\n".join(file.readlines())
#     file.close()
#     for pair in get_all_pair_name():
#         if pair[-4:] == "USDT":
#             file = open("trades/" + pair + ".py", "w")
#             file.write(file_pattern)
#             file.close()
#
#
# def all_open_orders() -> dict:  # 40
#     orders = json_to_improve_dict(CLIENT.get_open_orders(), key="symbol")
#     for order in orders:
#         orders[order]["time"] = binance_timestamp_to_datetime(int(orders[order]["time"]))
#         orders[order]["updateTime"] = binance_timestamp_to_datetime(int(orders[order]["updateTime"]))
#     return orders
#
#
# def all_open_orders_sorted() -> str:  # 40
#     return sorted_dict(all_open_orders(), key=lambda x: x[1]["time"], reverse=True)
#
#
# def get_assets_higher_than(dol: float):
#     return sorted(
#         ((asset_infos[0], asset_infos[1][0]) for asset_infos in bank_estimation()[1] if
#          float(asset_infos[1][0]) >= dol),
#         key=lambda x: 1 / x[1])
#
#

# if V["fast_sell"] and (V["v_candle_last_order"] > 3 or V["v_candle_last_order"] < -3):
#     take_profit_action()
#     continue
# # if (V["fast_sell"] and
# #         ((V["max_v_candle_last_order"] > 3 and V["v_candle_last_order"] < V[
# #             "max_v_candle_last_order"] / 2)
# #         or V["v_candle_last_order"] < -3)
# # ):
# #     if V["fast_sell_timer"] is None:
# #         V["fast_sell_timer"] = now()
# #     elif elapsed_seconds(V["fast_sell_timer"]) > 30:
# #         take_profit_action()
# #         V["fast_sell_timer"] = None
# # else:
# #     V["fast_sell_timer"] = None

if __name__ == '__main__':
    # print(bets_strategy(max_try=3))
    print(binance_timestamp_to_datetime(1679695173681))
    # print(bets_strategy_bollinger(bankroll=5000))
    # print(bets_strategy_bollinger()[0] * get_usd_price("btc"))
    # print(bets_strategy_bollinger()[0])
    # get_stepsize("BTCFDUSD")
    # get_minimal_order_devise_amount("BTCFDUSD")
    # a = get_all_pair_price_alive()
    # b = get_all_pair_price_dead()
    # c = get_all_pair_name_alive()
    # a = get_all_devises()
    # b = get_all_tokens()
    # c = get_all_actifs()
    # d = get_pair_highest_volume("USD", "BTC", "ETH", "BNB", "EUR")
    # 1
