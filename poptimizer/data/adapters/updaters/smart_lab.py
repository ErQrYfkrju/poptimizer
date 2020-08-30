"""Загрузка данных со https://www.smart-lab.ru."""
from typing import List

import pandas as pd

from poptimizer.data.adapters.updaters import connection, parser, logger
from poptimizer.data.ports import base, names, outer

# Параметры парсинга сайта
URL = "https://smart-lab.ru/dividends/index/order_by_cut_off_date/asc/"
TABLE_INDEX = 0
HEADER_SIZE = 1
FOOTER = "+добавить дивиденды"


def get_col_desc() -> List[parser.ColDesc]:
    """Формирует список с описанием нужных столбцов."""
    ticker = parser.ColDesc(num=1, raw_name=("Тикер",), name=names.TICKER, parser_func=None)
    date = parser.ColDesc(
        num=9,
        raw_name=("дата отсечки",),
        name=names.DATE,
        parser_func=parser.date_parser,
    )
    div = parser.ColDesc(
        num=5,
        raw_name=("дивиденд,руб",),
        name=names.DIVIDENDS,
        parser_func=parser.div_parser,
    )
    return [ticker, date, div]


class SmartLabUpdater(logger.LoggerMixin, outer.AbstractUpdater):
    """Обновление данных с https://www.smart-lab.ru."""

    def __call__(self, table_name: base.TableName) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        name = self._log_and_validate_group(table_name, base.SMART_LAB)
        if name != base.SMART_LAB:
            raise base.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        html = connection.get_html(URL)
        cols_desc = get_col_desc()
        table = parser.HTMLTable(html, TABLE_INDEX, cols_desc)
        df = table.get_df()
        if FOOTER not in df.index[-1]:
            raise base.DataError(f"Некорректная html-таблица {table_name}")
        return df.dropna()
