"""Вспомогательные функции для хранения данных."""
import asyncio
import logging
from datetime import datetime
from typing import Tuple, List, Dict, Any

import aiomoex
import pandas as pd

from poptimizer.store import mongo

# Метки столбцов данных
DATE = "DATE"
CLOSE = "CLOSE"
TURNOVER = "TURNOVER"
TICKER = "TICKER"
REG_NUMBER = "REG_NUMBER"
LOT_SIZE = "LOT_SIZE"
DIVIDENDS = "DIVIDENDS"

# Часовой пояс MOEX
MOEX_TZ = "Europe/Moscow"

# Торги заканчиваются в 19.00, но данные публикуются 19.45
END_OF_TRADING = dict(hour=19, minute=45, second=0, microsecond=0, nanosecond=0)

# Основная база
DB = "data"

# Коллекция для хранения вспомогательной информации и единичных данных
MISC = "misc"


def now_and_end_of_trading_day() -> Tuple[datetime, datetime]:
    """Конец последнего торгового дня в UTC."""
    now = pd.Timestamp.now(MOEX_TZ)
    end_of_trading = now.replace(**END_OF_TRADING)
    if end_of_trading > now:
        end_of_trading += pd.DateOffset(days=-1)
    return now.astimezone(None), end_of_trading.astimezone(None)


async def get_board_dates() -> List[Dict[str, str]]:
    """TODO: заменить и добавить тесты."""
    async with aiomoex.ISSClientSession():
        return await aiomoex.get_board_dates(
            board="TQBR", market="shares", engine="stock"
        )


def last_history_from_doc(doc: Dict[str, Any]) -> datetime:
    """Момент времени UTC публикации данных о последних торгах, которая есть на MOEX ISS."""
    date = pd.Timestamp(doc["data"][0]["till"], tz=MOEX_TZ)
    return date.replace(**END_OF_TRADING).astimezone(None)


def get_last_history_date(db: str = DB, collection: str = MISC) -> datetime:
    """"Момент времени UTC после, которого не нужно обновлять данные."""
    misc_collection = mongo.MONGO_CLIENT[db][collection]
    doc = misc_collection.find_one({"_id": "last_date"})
    now, end_of_trading = now_and_end_of_trading_day()
    if doc is None or doc["timestamp"] < end_of_trading:
        data = asyncio.run(get_board_dates())
        doc = dict(_id="last_date", data=data, timestamp=now)
        misc_collection.replace_one({"_id": "last_date"}, doc, upsert=True)
        logging.info(f"Последняя дата с историей: {last_history_from_doc(doc).date()}")
    return last_history_from_doc(doc)
