import sys
import logging
from fastapi import FastAPI


# Настройка логирования ГЛОБАЛЬНО
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,
)

# все logger = logging.getLogger(__name__) используют эти настройки
logger = logging.getLogger(__name__)

logger.info("Запуск приложения в main")

app = FastAPI(title="Events provider")

logger.info("Запущен app")

@app.get("/")
async def root():
    return {
        "service": "Events provider",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "succses"}
