from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 🔹 Настройки подключения
DB_USER = "macook"          # пользователь PostgreSQL
DB_PASSWORD = "1234"        # пароль, который ты установила через ALTER USER
DB_HOST = "localhost"       # адрес сервера (локально)
DB_PORT = "5432"            # порт PostgreSQL
DB_NAME = "linguaai"        # твоя база данных

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 🔹 Создаём движок SQLAlchemy
engine = create_engine(DATABASE_URL, echo=True)

# 🔹 Базовый класс для моделей
Base = declarative_base()

# 🔹 Сессия для работы с базой
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# 🔹 Пример функции для получения сессии
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
