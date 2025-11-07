from sqlalchemy import Column, Integer, String
from .database import Base
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.sql import func
from enum import Enum
from sqlalchemy import Column, String, Enum as SqlEnum


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False) 
    flashcards = relationship("Flashcard", back_populates="user")


class FlashcardStatus(str, Enum):
    NEW = "new"
    INPROGRESS = "inprogress"
    DONE = "done"
 
class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(SqlEnum(FlashcardStatus), nullable=False, default=FlashcardStatus.NEW)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="flashcards")