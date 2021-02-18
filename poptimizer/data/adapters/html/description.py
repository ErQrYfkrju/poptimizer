"""Описание колонок для парсера html-таблиц."""
import re
from datetime import datetime
from typing import Callable, Final, NamedTuple, Optional, Union

import pandas as pd

from poptimizer import config
from poptimizer.shared import col

# Параметры проверки обыкновенная акция или привилегированная
COMMON_TICKER_LENGTH: Final = 4
PREFERRED_TICKER_ENDING: Final = "P"

DIV_PATTERN: Final = r".*\d"
DIV_PATTERN_US: Final = r"\$(.*\d)"
DIV_PATTERN_WITH_CUR = r".*\d\s{1,2}[$₽]"
DATE_PATTERN: Final = r"\d{1,2}\.\d{2}\.\d{4}"
DATE_PATTERN_US: Final = r"\d{2}\/\d{2}\/\d{4}"


class ParserError(config.POptimizerError):
    """Ошибки в парсинге html-таблиц."""


def is_common(ticker: str) -> bool:
    """Определяет является ли акция обыкновенной."""
    if len(ticker) == COMMON_TICKER_LENGTH:
        return True
    elif len(ticker) == COMMON_TICKER_LENGTH + 1:
        if ticker[COMMON_TICKER_LENGTH] == PREFERRED_TICKER_ENDING:
            return False
    raise ParserError(f"Некорректный тикер {ticker}")


ParserFunc = Callable[[str], Union[None, float, datetime]]


class ColDesc(NamedTuple):
    """Описание столбца с данными.

    Используется для выбора определенных столбцов из html-таблицы, проверки ожидаемых значений в
    заголовках и преобразования из строк в нужный формат.

    - num: номер столбца
    - raw_name: часть исходного наименования для валидации
    - name: целевое наименование столбца
    - parser_func: функция для парсинга значений
    """

    num: int
    raw_name: tuple[str, ...]
    name: str
    parser_func: Optional[ParserFunc]


def date_parser(date: str) -> Optional[datetime]:
    """Функция парсинга значений в столбце с датами закрытия реестра."""
    re_date = re.search(DATE_PATTERN, date)
    if re_date:
        date_string = re_date.group(0)
        return datetime.strptime(date_string, "%d.%m.%Y")  # noqa: WPS323
    return None


def date_parser_us(date: str) -> Optional[datetime]:
    """Парсинг даты в американском формате."""
    re_date = re.search(DATE_PATTERN_US, date)
    if re_date:
        date_string = re_date.group(0)
        return datetime.strptime(date_string, "%m/%d/%Y")  # noqa: WPS323
    return None


def div_parser(div: str) -> Optional[float]:
    """Функция парсинга значений в столбце с дивидендами."""
    re_div = re.search(DIV_PATTERN, div)
    if re_div:
        div_string = re_div.group(0)
        div_string = div_string.replace(",", ".")
        div_string = div_string.replace(" ", "")
        return float(div_string)
    return None


def div_parser_us(div: str) -> Optional[float]:
    """Функция парсинга дивидендов в долларах."""
    re_div = re.search(DIV_PATTERN_US, div)
    if re_div:
        div_string = re_div.group(1)
        div_string = div_string.replace(",", ".")
        div_string = div_string.replace(" ", "")
        return float(div_string)
    return None


def div_parser_with_cur(div: str) -> Optional[str]:
    """Функция парсинга дивидендов с валютой в конце."""
    re_div = re.search(DIV_PATTERN_WITH_CUR, div)
    if re_div:
        div_string = re_div.group(0)
        div_string = div_string.replace(",", ".")
        div_string = div_string.replace(" ", "")
        div_string = div_string.replace("₽", col.RUR)
        return div_string.replace("$", col.USD)
    return None


def reformat_df_with_cur(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Разделяет столбец на валюту и значение."""
    ticker_col = df[ticker]
    df[col.CURRENCY] = ticker_col.str.slice(start=-3)
    ticker_col = ticker_col.str.slice(stop=-3).str.strip()  # "27 "
    df[ticker] = pd.to_numeric(ticker_col)
    return df
