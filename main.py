import os
import logging
from fastapi import FastAPI, Request, HTTPException
import requests
import uvicorn

# Настройка логирования для Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    logger.error("🚨 ОШИБКА: Переменная окружения DEEPSEEK_API_KEY не установлена!")
else:
    logger.info("✅ API ключ DeepSeek загружен")

@app.get("/")
async def get_root():
    return {"message": "Сервер работает. Используйте POST / для общения с Алисой."}

@app.post("/")
async def main(request: Request):
    try:
        # 1. Получаем текст от Алисы
        body = await request.json()
        user_text = body.get("request", {}).get("original_utterance", "")
        
        if not user_text:
            logger.warning("Пустой запрос от Алисы")
            return {
                "version": body.get("version", "1.0"),
                "session": body.get("session", {}),
                "response": {
                    "text": "Я не расслышала текст. Повторите, пожалуйста.",
                    "end_session": False
                }
            }

        logger.info(f"📩 Запрос от Алисы: {user_text[:50]}...")

        # 2. Проверка API ключа
        if not DEEPSEEK_API_KEY:
            logger.error("❌ API ключ DeepSeek отсутствует!")
            raise HTTPException(status_code=500, detail="API ключ DeepSeek не настроен")

        # 3. Запрос к DeepSeek
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": user_text}],
            "temperature": 0.7,
            "max_tokens": 500
        }

        logger.info("🔄 Отправляю запрос к DeepSeek API...")
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        
        logger.info(f"📡 Статус ответа от DeepSeek: {response.status_code}")

        # 4. Проверка ответа от DeepSeek
        if response.status_code != 200:
            error_msg = f"DeepSeek вернул ошибку {response.status_code}: {response.text[:200]}"
            logger.error(error_msg)
            return {
                "version": body.get("version", "1.0"),
                "session": body.get("session", {}),
                "response": {
                    "text": f"Извините, сервис временно недоступен. Ошибка: {response.status_code}",
                    "end_session": False
                }
            }

        # 5. Парсим ответ
        data = response.json()
        
        if "choices" not in data or len(data["choices"]) == 0:
            logger.error(f"Неожиданный ответ от DeepSeek: {data}")
            return {
                "version": body.get("version", "1.0"),
                "session": body.get("session", {}),
                "response": {
                    "text": "Извините, я не смогла обработать ответ от сервера.",
                    "end_session": False
                }
            }

        answer = data["choices"][0]["message"]["content"]
        logger.info(f"✅ Ответ от DeepSeek получен, длина: {len(answer)} символов")

        # 6. Отдаем ответ Алисе
        return {
            "version": body.get("version", "1.0"),
            "session": body.get("session", {}),
            "response": {
                "text": answer,
                "end_session": False
            }
        }

    except requests.exceptions.Timeout:
        logger.error("⏰ Таймаут при запросе к DeepSeek API")
        return {
            "version": body.get("version", "1.0"),
            "session": body.get("session", {}),
            "response": {
                "text": "Сервер долго не отвечает. Попробуйте позже.",
                "end_session": False
            }
        }
    except Exception as e:
        logger.error(f"💥 Непредвиденная ошибка: {str(e)}", exc_info=True)
        return {
            "version": body.get("version", "1.0"),
            "session": body.get("session", {}),
            "response": {
                "text": f"Произошла внутренняя ошибка: {str(e)[:100]}",
                "end_session": False
            }
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)