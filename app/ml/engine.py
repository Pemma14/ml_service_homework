import logging
from typing import Any, Dict, List

from app.utils import MLInferenceException, MLInvalidDataException, MLModelLoadException

logger = logging.getLogger(__name__)

class MLEngine:
    """
    Сервис для работы с ML-моделью (scikit-learn).
    Отвечает исключительно за загрузку модели, препроцессинг и инференс.
    """

    def __init__(self):
        try:
            # В реальном приложении здесь была бы загрузка .pkl файла
            # self.model = joblib.load("model.pkl")
            self.model = None
            logger.info("ML Engine инициализирован (режим заглушки для LogisticRegression)")
        except Exception as e:
            logger.critical(f"Критическая ошибка при инициализации ML-модели: {e}")
            raise MLModelLoadException()

    def predict(self, items: List[Dict[str, Any]]) -> List[str]:
        """
        Инференс ML-модели.
        """
        try:
            return self._run_inference(items)
        except Exception as e:
            logger.error(f"Ошибка во время выполнения инференса: {e}")
            raise MLInferenceException()

    def _run_inference(self, items: List[Dict[str, Any]]) -> List[str]:
        """
        Синхронная логика работы scikit-learn.
        """
        try:
            results = []
            for item in items:
                features = item.get("features")
                # Имитация работы логистической регрессии
                # В реальности: prediction = self.model.predict([features])[0]
                probability = 0.75  # Заглушка: вероятность ответа на лечение
                label = "Responder" if probability > 0.5 else "Non-responder"
                results.append(f"Result: {label} (confidence: {probability})")

            return results
        except Exception as e:
            # Здесь ловим ошибки самой модели или данных (например, ValueError от sklearn)
            logger.error(f"Ошибка внутри _run_inference: {e}")
            raise MLInferenceException()

    @staticmethod
    def validate_features(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Специфичная для модели валидация входных признаков.
        Если есть ошибки, выбрасывает MLInvalidDataException.
        """
        valid_items = []
        errors = []
        for i, item in enumerate(items):
            features = item.get("features")
            # Допустим, для нашей регрессии нужно ровно 5 числовых признаков
            if not features or not isinstance(features, list):
                errors.append({"index": i, "error": "Features must be a list"})
            elif len(features) != 5:
                errors.append({"index": i, "error": f"Model requires 5 features, got {len(features)}"})
            else:
                valid_items.append(item)

        if errors:
            logger.warning(f"Обнаружены ошибки в данных ({len(errors)} шт.). Валидация не пройдена.")
            raise MLInvalidDataException(errors=errors)

        return valid_items

# Создаем единственный экземпляр (Singleton) движка
ml_engine = MLEngine()
