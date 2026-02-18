import logging
import os
from typing import Any, Dict, List
import joblib
import pandas as pd
from ml_worker.config import settings

class MLModelLoadException(Exception):
    """Исключение при загрузке модели."""
    pass

class MLInferenceException(Exception):
    """Исключение во время инференса."""
    pass

logger = logging.getLogger(__name__)

class MLEngine:
    """
    Сервис для работы с ML-моделью. Отвечает за загрузку модели и выполнение предсказаний.
    """

    def __init__(self):
        self._model = None
        self.model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml_worker/model.pkl")

    @property
    def model(self):
        """Ленивая загрузка модели."""
        if self._model is None:
            try:
                if os.path.exists(self.model_path):
                    self._model = joblib.load(self.model_path)
                    logger.info(f"ML модель успешно загружена из {self.model_path}")
                else:
                    logger.warning(f"Файл модели не найден по пути {self.model_path}, включен режим заглушки")
            except Exception as e:
                logger.critical(f"Критическая ошибка при загрузке ML-модели: {e}")
                raise MLModelLoadException()
        return self._model

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
                return ["выраженные побочные эффекты будут с вероятностью 0.15"] * len(items)

            # Создаем DataFrame для сохранения правильного порядка и имен колонок
            features_order = settings.worker.FEATURES_ORDER

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
                    # p0 = round(float(prob[0]), 2)
                    p1 = round(float(prob[1]), 2)
                    results.append(f"выраженные побочные эффекты будут с вероятностью {p1}")

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


def get_ml_engine() -> MLEngine:
    """Зависимость для получения экземпляра ML-движка."""
    return ml_engine
