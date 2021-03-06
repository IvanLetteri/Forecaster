"""
forecaster.enums
~~~~~~~~~~~~~~

Contains all Enums and dicts used in package.
"""

from enum import Enum, auto


class EVENTS(Enum):
    MISSING_DATA = auto()
    MODE_FAILURE = auto()
    CLOSED_POS = auto()
    MARKET_CLOSED = auto()
    CONNECTION_ERROR = auto()


class ACTIONS(Enum):
    START_BOT = auto()
    STOP_BOT = auto()
    SHUTDOWN = auto()
    PREDICT = auto()
    CHANGE_MODE = auto()
    BUY = 'buy'
    SELL = 'sell'


TIMEFRAME = {
    '1d': 60 * 60 * 24,
    '4h': 60 * 60 * 4,
    '1h': 60 * 60,
    '15m': 60 * 15,
    '10m': 60 * 10,
    '5m': 60 * 5,
    '1m': 60
}
