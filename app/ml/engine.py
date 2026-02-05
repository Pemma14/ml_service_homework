import logging
import os
from typing import Any, Dict, List
import joblib
import pandas as pd

from app.utils import MLInferenceException, MLModelLoadException

logger = logging.getLogger(__name__)

class MLEngine:
    """
    Сервис для работы с ML-моделью. Отвечает за загрузку модели и выполнение предсказаний.
    """

    def __init__(self):
        try:
            model_path = os.path.join(os.path.dirname(__file__), "model.pkl")
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                logger.info(f"ML модель успешно загружена из {model_path}")
            else:
                self.model = None
                logger.warning(f"Файл модели не найден по пути {model_path}, включен режим заглушки")
        except Exception as e:
            logger.critical(f"Критическая ошибка при инициализации ML-модели: {e}")
            raise MLModelLoadException()

    def predict(self, items: List[Any]) -> List[str]:
        try:
            # Конвертируем объекты Pydantic в словари, если нужно
            data_to_predict = []
            for item in items:
                if hasattr(item, "model_dump"):
                    data_to_predict.append(item.model_dump(by_alias=True))
                else:
                    data_to_predict.append(item)

            return self._run_inference(data_to_predict)
        except Exception as e:
            logger.error(f"Ошибка во время выполнения инференса: {e}")
            raise MLInferenceException()

    def _run_inference(self, items: List[Dict[str, Any]]) -> List[str]:
        try:
            if self.model is None:
                return [
                    "выраженных побочных ответов не будет с вероятностью 0.85, "
                    "выраженные побочные эффекты будут с вероятностью 0.15"
                    for _ in items
                ]

            # Создаем DataFrame для сохранения правильного порядка и имен колонок
            features_order = [
                'Возраст', 'ВНН/ПП', 'Клозапин',
                'CYP2C19 1/2', 'CYP2C19 1/17', 'CYP2C19 *17/*17', 'CYP2D6 1/3'
            ]

            df = pd.DataFrame(items)

            # Добавляем недостающие колонки (если есть) и выстраиваем их в нужном порядке
            for col in features_order:
                if col not in df.columns:
                    df[col] = 0

            df = df[features_order]

            results = []
            # Пробуем получить вероятности для оценки уверенности
            try:
                probabilities = self.model.predict_proba(df)
                for prob in probabilities:
                    # В scikit-learn для бинарной классификации prob[0] - вероятность класса 0, prob[1] - класса 1
                    # Мы выяснили, что классы модели [0, 1]
                    p0 = round(float(prob[0]), 2)
                    p1 = round(float(prob[1]), 2)
                    results.append(
                        f"выраженные побочные эффекты будут с вероятностью {p1}"
                    )
            except (AttributeError, Exception) as e:
                logger.warning(f"Модель не поддерживает predict_proba или произошла ошибка: {e}")
                # Если модель не поддерживает predict_proba, используем просто predict
                predictions = self.model.predict(df)
                for pred in predictions:
                    if pred == 0:
                        results.append("выраженных побочных ответов не будет")
                    else:
                        results.append("выраженные побочные эффекты будут")

            return results
        except Exception as e:
            logger.error(f"Ошибка внутри _run_inference: {e}")
            raise MLInferenceException()


# Создаем единственный экземпляр (Singleton) движка
ml_engine = MLEngine()
