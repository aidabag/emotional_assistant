import os
from openai import OpenAI
from typing import List, Dict, Optional

# Системная подсказка для ассистента саморефлексии
SYSTEM_PROMPT = """Ты — ассистент для саморефлексии. Твоя задача:
1) Определить эмоциональный тон текста (спокойный, радостный, грустный, тревожный, раздражённый и т.д.).
2) Вернуть краткий (1-3 предложения) нейтральный отклик, отражающий эмоцию.
3) Предложить 1–2 открытых вопроса для саморефлексии (например: "Что случилось, что вызвало это чувство?").
4) Никогда не давай медицинских советов, не ставь диагнозов, не предлагай лечение.
5) Если текст содержит упоминания о самоубийстве, причинении вреда себе или другим — вежливо и однозначно предложи обратиться к специалистам и экстренным службам, и выдать общую информацию о горячих линиях.
6) Всегда используй факты/правила из предоставленных источников (RAG фрагментов), когда уместно, и указывай, что ответ основан на доступных материалах.
"""


class YandexAdapter:
    """Адаптер для работы с Yandex Cloud Responses API"""

    def __init__(self):
        # Получение API ключа и ID папки из переменных окружения
        self.api_key = os.getenv("YANDEX_API_KEY")
        self.folder_id = os.getenv("YANDEX_FOLDER_ID")
        self.model = f"gpt://{self.folder_id}/yandexgpt/rc"

        # Проверка обязательных переменных окружения
        if not self.api_key or not self.folder_id:
            raise ValueError("YANDEX_API_KEY и YANDEX_FOLDER_ID должны быть установлены")

        # Инициализация клиента OpenAI с настройками Yandex
        self.client = OpenAI(
            base_url="https://rest-assistant.api.cloud.yandex.net/v1",
            api_key=self.api_key,
            project=self.folder_id
        )

    def format_rag_context(self, rag_chunks: List[Dict]) -> str:
        """
        Форматирование RAG фрагментов в единый контекст для модели
        
        :param rag_chunks: список фрагментов RAG
        :return: строка контекста
        """
        if not rag_chunks:
            return ""

        context_parts = ["Контекст из доступных материалов:\n"]
        for i, chunk in enumerate(rag_chunks, 1):
            source = chunk.get("source", "unknown")
            content = chunk.get("content", "")
            context_parts.append(f"[{i}] Источник: {source}\n{content}\n")

        return "\n".join(context_parts)

    def detect_crisis_keywords(self, message: str) -> bool:
        """
        Определение наличия кризисных ключевых слов в сообщении
        
        :param message: текст сообщения
        :return: True, если обнаружены слова, связанные с опасностью
        """
        crisis_keywords = [
            "самоубийство", "суицид", "убить себя", "покончить с собой",
            "навредить себе", "причинить вред", "хочу умереть",
            "нет смысла жить", "конец всему"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in crisis_keywords)

    def send_message(
        self,
        message: str,
        rag_chunks: List[Dict] = None,
        previous_response_id: Optional[str] = None
    ) -> Dict:
        """
        Отправка сообщения в Yandex Cloud Responses API
        
        :param message: текст сообщения пользователя
        :param rag_chunks: список RAG фрагментов для контекста
        :param previous_response_id: ID предыдущего ответа для непрерывности диалога
        :return: словарь с ключами 'response_text' и 'response_id'
        """
        # Формирование контекста с RAG
        rag_context = ""
        if rag_chunks:
            rag_context = self.format_rag_context(rag_chunks)

        # Формирование полного входа для модели
        if rag_context:
            full_input = f"{rag_context}\n\nСообщение пользователя: {message}"
        else:
            full_input = message

        try:
            # Параметры запроса к API
            kwargs = {
                "model": self.model,
                "instructions": SYSTEM_PROMPT,
                "input": full_input,
                "store": True,
                "reasoning": {"effort": "low"}
            }

            if previous_response_id:
                kwargs["previous_response_id"] = previous_response_id

            # Отправка запроса и получение ответа
            response = self.client.responses.create(**kwargs)

            return {
                "response_text": response.output_text,
                "response_id": response.id
            }

        except Exception as e:
            raise Exception(f"Ошибка Yandex API: {str(e)}")


# Глобальный экземпляр адаптера (для повторного использования)
_adapter_instance = None


def get_adapter() -> YandexAdapter:
    """
    Получение или создание экземпляра адаптера
    
    :return: объект YandexAdapter
    """
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = YandexAdapter()
    return _adapter_instance
