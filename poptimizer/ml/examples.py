"""Набор обучающих примеров."""
from typing import Tuple

import pandas as pd

from poptimizer.config import POptimizerError
from poptimizer.ml import feature

ON_OFF = [True, False]

ML_PARAMS = (
    (
        (feature.Label, {"days": 22}),
        (feature.STD, {"on_off": True, "days": 20}),
        (feature.Ticker, {"on_off": True}),
        (feature.Mom12m, {"on_off": True, "days": 251}),
        (feature.DivYield, {"on_off": True, "days": 253}),
        (feature.Mom1m, {"on_off": True, "days": 21}),
        (feature.Min1m, {"on_off": True, "days": 22}),
    ),
    {
        "bagging_temperature": 1.041_367_726_420_619,
        "depth": 5,
        "l2_leaf_reg": 2.764_496_778_258_427_3,
        "learning_rate": 0.060_435_197_338_608_936,
        "one_hot_max_size": 100,
        "random_strength": 1.376_092_249_675_814_1,
        "ignored_features": [],
    },
)


class Examples:
    """Позволяет сформировать набор обучающих примеров и меток к ним.

    Разбить данные на обучающую и валидирующую выборку или получить полный набор данных.
    """

    def __init__(self, tickers: Tuple[str, ...], date: pd.Timestamp, params: tuple):
        """Обучающие примеры состоят из признаков на основе данных для тикеров до указанной даты.

        :param tickers:
            Тикеры, для которых нужно составить обучающие примеры.
        :param date:
            Последняя дата, до которой можно использовать данные.
        :param params:
            Параметры ML-модели.
        """
        self._tickers = tickers
        self._date = date
        self._features = [
            cls(tickers, date, feat_params) for cls, feat_params in params[0]
        ]

    def get_features_names(self):
        """Название признаков."""
        return [feat.name for feat in self._features[1:]]

    def categorical_features(self):
        """Массив с указанием номеров признаков с категориальными данными."""
        return [n for n, feat in enumerate(self._features[1:]) if feat.is_categorical()]

    def get_params_space(self):
        """Формирует общее вероятностное пространство модели.

        Массив из кортежей:

        * первый элемент - используется признак или нет
        * второй элемент - подпространство для параметров признака

        Метка данных включается всегда.
        """
        it = iter(self._features)
        label = next(it)
        space = [(True, label.get_params_space())]
        for feat in it:
            space.append(
                [True, feat.get_params_space()]
            )  # hp.choice(feat.name, ON_OFF)
        return space

    def get(self, date: pd.Timestamp, params=None):
        """Получить обучающие примеры для одной даты.

        Значение признаков создается в том числе для не используемых признаков.
        Метки нормируются по СКО.
        """
        data = [
            feat.get(date, **value) for feat, (_, value) in zip(self._features, params)
        ]
        data[0] /= data[1]
        df = pd.concat(data, axis=1)
        return df[df.iloc[:, 1] != 0]

    @staticmethod
    def mean_std_days(params):
        """Количество дней, которое использовалось для расчета СКО для нормировки."""
        return params[0][1]["days"], params[1][1]["days"]

    def learn_pool_params(self, params):
        """Данные для создание catboost.Pool с обучающими примерами."""
        label = self._features[0]
        days = params[0][1]["days"]
        index = label.index
        try:
            loc = index.get_loc(self._date)
        except KeyError:
            raise POptimizerError(
                f"Для даты {self._date.date()} отсутствуют исторические котировки"
            )
        last_learn = loc - days
        index = index[last_learn::-days]
        data = [self.get(date, params) for date in index]
        df = pd.concat(data, axis=0, ignore_index=True)
        df.dropna(axis=0, inplace=True)
        return dict(
            data=df.iloc[:, 1:],
            label=df.iloc[:, 0],
            cat_features=self.categorical_features(),
            feature_names=list(df.columns[1:]),
        )

    def predict_pool_params(self, params):
        """Данные для создание catboost.Pool с примерами для прогноза."""
        df = self.get(self._date, params)
        return dict(
            data=df.iloc[:, 1:],
            label=None,
            cat_features=self.categorical_features(),
            feature_names=list(df.columns[1:]),
        )
