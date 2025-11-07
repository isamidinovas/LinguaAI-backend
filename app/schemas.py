from pydantic import BaseModel, EmailStr, validator
from datetime import datetime
from enum import Enum
from typing import List

# User Schemas
class UserSignup(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    confirm_password: str

    @validator("password")
    def password_max_length(cls, v):
        if len(v.encode('utf-8')) > 72:
            raise ValueError("Password too long (max 72 bytes)")
        return v[:72]  # Обрезаем до 72 байт

    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v

class UserLogin(BaseModel):
    full_name: str
    password: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

# Flashcard Schemas

class FlashcardStatusEnum(str, Enum):
    NEW = "new"
    INPROGRESS = "inprogress"
    DONE = "done"

class FlashcardBase(BaseModel):
    question: str
    answer: str
    status: FlashcardStatusEnum = FlashcardStatusEnum.NEW


class FlashcardCreate(BaseModel):
    question: str
    answer: str
    status: FlashcardStatusEnum = FlashcardStatusEnum.NEW

class FlashcardResponse(BaseModel):
    id: int
    question: str
    answer: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    user:UserResponse
    class Config:
        orm_mode = True


class UserWithFlashcardsResponse(BaseModel):
    id: int
    full_name: str
    email: str
    flashcards: List[FlashcardResponse] = []

    class Config:
        orm_mode = True