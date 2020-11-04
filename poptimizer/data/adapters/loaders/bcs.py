"""Загрузка данных по дивидендам с сайта https://bcs-express.ru."""
import re
from datetime import datetime
from typing import List, Optional, cast

import bs4
import pandas as pd

from poptimizer.data.adapters import logger
from poptimizer.data.adapters.html import parser
from poptimizer.data.ports import outer
from poptimizer.data_di.shared import col

URL = "https://bcs-express.ru/kotirovki-i-grafiki/"
DATE_TAG_RE = re.compile(".*_close-date.*")
DATE_PATTERN = re.compile(r"\d{2}\.\d{2}\.\d{4}")
DIV_TAG_RE = re.compile(".*_value.*")

DIV_TAG = "div"
CLASS_TAG = "class"


async def _get_rows(ticker: str) -> List[bs4.BeautifulSoup]:
    """Получает строки таблицы с дивидендами в формате bs4."""
    html = await parser.get_html(URL + ticker)
    soup = bs4.BeautifulSoup(html, "lxml")
    div_table = soup.find(DIV_TAG, {CLASS_TAG: "dividends-table js-div-table"})
    if div_table is None:
        return []
    rows = div_table.find_all(DIV_TAG, {CLASS_TAG: "dividends-table__row _item"})
    return cast(List[bs4.BeautifulSoup], rows)


def _parse_date(row: bs4.BeautifulSoup) -> Optional[datetime]:
    """Парсит даты из строки таблицы."""
    soup = row.find(DIV_TAG, {CLASS_TAG: DATE_TAG_RE}, string=DATE_PATTERN)
    if soup:
        return datetime.strptime(soup.string.strip(), "%d.%m.%Y")  # noqa: WPS323
    return None


def _parse_div(row: bs4.BeautifulSoup) -> float:
    """Парсит дивиденды из строки таблицы."""
    soup = row.find(DIV_TAG, {CLASS_TAG: DIV_TAG_RE})
    div_string = soup.string
    div_string = div_string.replace(",", ".")
    div_string = div_string.replace(" ", "")
    return float(div_string)


class BCS(logger.LoaderLoggerMixin, outer.AbstractLoader):
    """Обновление данных с https://bcs-express.ru."""

    async def get(self, table_name: outer.TableName) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        ticker = self._log_and_validate_group(table_name, outer.BCS)

        rows = await _get_rows(ticker)
        div_data = [(_parse_date(row), _parse_div(row)) for row in rows]

        df = pd.DataFrame(data=div_data, columns=[col.DATE, ticker])
        df = df.set_index(col.DATE)
        df = df.sort_index(axis=0)
        return df.groupby(lambda date: date).sum()
