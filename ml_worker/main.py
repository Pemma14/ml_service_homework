import asyncio
import logging
import os
import signal
import sys
from ml_worker.services.ml_worker import MLWorker
from ml_worker.services.rpc_worker import RPCWorker

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MLWorkerMain")

def create_worker(mode: str, worker_id: str):
    """
    Фабрика для создания воркеров по аналогии с примером преподавателя.
    """
    if mode == 'ml':
        return MLWorker(worker_id=worker_id)
    if mode == 'rpc':
        return RPCWorker(worker_id=worker_id)
    raise ValueError(f"Неизвестный режим воркера: {mode}")

async def main():
    mode = os.getenv("WORKER_MODE", "ml")
    worker_id = os.getenv("WORKER_ID", "ml_worker-1")

    logger.info(f"Старт воркера {worker_id} (режим: {mode})")

    worker = create_worker(mode, worker_id)

    loop = asyncio.get_running_loop()

    # Обработка сигналов для корректного завершения
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))

    try:
        await worker.run()
    except asyncio.CancelledError:
        logger.info(f"Работа воркера {worker_id} прервана.")
    except Exception as e:
        logger.error(f"Критический сбой в основном цикле: {e}")
        return 1
    finally:
        logger.info(f"Воркер {worker_id} завершил работу.")
    return 0

if __name__ == "__main__":
    # Код выхода для системы
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        logger.info("Воркер остановлен пользователем.")
        sys.exit(0)
