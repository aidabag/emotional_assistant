from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Базовый класс для моделей SQLAlchemy
Base = declarative_base()


class Message(Base):
    """Модель сообщения для хранения истории диалогов"""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)  # Уникальный идентификатор сообщения
    session_id = Column(String, nullable=False, index=True)    # Идентификатор сессии пользователя
    role = Column(String, nullable=False)                     # Роль: 'user' или 'assistant'
    content = Column(Text, nullable=False)                    # Текст сообщения
    response_id = Column(String, nullable=True)               # ID ответа ассистента для связи сообщений
    created_at = Column(DateTime, default=datetime.utcnow)    # Время создания записи


# Настройка подключения к базе данных
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/db.sqlite")

# Создание директории для SQLite базы данных, если она не существует
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Создание движка базы данных
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Создание сессии для работы с базой данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Инициализация таблиц базы данных"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Получение сессии для работы с базой данных.
    Используется в зависимости FastAPI для автоматического закрытия сессии.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_message(db, session_id: str, role: str, content: str, response_id: str = None):
    """
    Сохранение сообщения в базу данных.
    
    :param db: объект сессии базы данных
    :param session_id: идентификатор сессии пользователя
    :param role: роль отправителя ('user' или 'assistant')
    :param content: текст сообщения
    :param response_id: идентификатор ответа ассистента (для связи сообщений)
    :return: объект сохраненного сообщения
    """
    message = Message(session_id=session_id, role=role, content=content, response_id=response_id)
    db.add(message)
    db.commit()
    return message


def get_last_response_id(db, session_id: str) -> str:
    """
    Получение идентификатора последнего ответа ассистента для конкретной сессии.
    Используется для обеспечения непрерывности диалога.
    
    :param db: объект сессии базы данных
    :param session_id: идентификатор сессии пользователя
    :return: ID последнего ответа или None, если ответов нет
    """
    last_message = db.query(Message).filter(
        Message.session_id == session_id,
        Message.role == "assistant",
        Message.response_id.isnot(None)
    ).order_by(Message.created_at.desc()).first()
    return last_message.response_id if last_message else None


def get_session_history(db, session_id: str, limit: int = 50):
    """
    Получение истории сообщений сессии.
    
    :param db: объект сессии базы данных
    :param session_id: идентификатор сессии пользователя
    :param limit: максимальное количество сообщений для получения
    :return: список сообщений сессии в порядке от последних к первым
    """
    return db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at.desc()).limit(limit).all()
