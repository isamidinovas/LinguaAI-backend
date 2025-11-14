from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import or_
from jose import JWTError, jwt
from fastapi import APIRouter 
import os
from dotenv import load_dotenv
import google.generativeai as genai
from app.database import get_db, Base, engine
from app.models import User, Flashcard, Languages
from app.schemas import (
    UserLogin, UserSignup, UserResponse, Token, 
    FlashcardCreate, FlashcardResponse, 
    UserWithFlashcardsResponse, FlashcardStatusEnum,
    LanguageResponse, LanguageCreate,
    FlashcardsPaginatedResponse, AIMessageRequest
)
from app.auth import (
    verify_password, create_access_token, 
    get_password_hash, SECRET_KEY, ALGORITHM
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response

load_dotenv()
# Создать таблицы, если их нет
Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "http://127.0.0.1:8000",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ========== OAuth2 и текущий пользователь ==========
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        full_name: str = payload.get("sub")
        if full_name is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.full_name == full_name).first()
    if user is None:
        raise credentials_exception
    return user


# ========== Роутеры ==========

# Роутер для аутентификации
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

@auth_router.post("/register")
def signup(user: UserSignup, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        full_name=user.full_name,
        email=user.email,
        password=get_password_hash(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "message": "User registered successfully",
        "user": {"full_name": new_user.full_name, "email": new_user.email}
    }

@auth_router.post("/login")
def login(user: UserLogin, response: Response, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.full_name == user.full_name).first()
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid full name or password")

    access_token = create_access_token({"sub": db_user.full_name})

    # Устанавливаем HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # локально без https
        max_age=3600
    )

    return {"message": "Login successful"}


@auth_router.post("/logout")
def logout(response: Response):
    # Устанавливаем cookie с пустым значением и max_age=0, чтобы удалить её
    response.delete_cookie(
        key="access_token",
        path="/"
    )
    return {"message": "Logged out successfully"}

    
def logout():
    return {"message": "Logout successful"} 
# Роутер для пользователей
users_router = APIRouter(prefix="/users", tags=["Users"])

@users_router.get("", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@users_router.get("/me", response_model=UserWithFlashcardsResponse)
def read_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    flashcards = db.query(Flashcard).filter(Flashcard.user_id == current_user.id).all()
    
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "flashcards": flashcards
    }


# Роутер для флешкарт
flashcards_router = APIRouter(prefix="/flashcards", tags=["Flashcards"])

@flashcards_router.post("", response_model=FlashcardResponse, status_code=201)
def create_flashcard(
    flashcard: FlashcardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    language = db.query(Languages).filter_by(code=flashcard.language_code).first()
    if not language:
        raise HTTPException(status_code=404, detail="Language not found")
    
    db_flashcard = Flashcard(
        question=flashcard.question,
        answer=flashcard.answer,
        topic=flashcard.topic,
        status=FlashcardStatusEnum.NEW,
        user_id=current_user.id,
        language_id=language.id
    )
    
    db.add(db_flashcard)
    db.commit()
    db.refresh(db_flashcard)
    return db_flashcard

@flashcards_router.get("", response_model=FlashcardsPaginatedResponse)
def get_flashcards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
):
    query = db.query(Flashcard).filter(Flashcard.user_id == current_user.id)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Flashcard.question.ilike(pattern),
                Flashcard.answer.ilike(pattern),
            )
        )

    total = query.count()
    items = query.offset(skip).limit(limit).all()

    return {"total": total, "items": items}

@flashcards_router.get("/statuses")
def get_flashcard_statuses():
    return [status.value for status in FlashcardStatusEnum]

@flashcards_router.get("/{flashcard_id}", response_model=FlashcardResponse)
def get_flashcard(
    flashcard_id: int,
    db: Session = Depends(get_db),
):
    db_flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
    if not db_flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    return db_flashcard

@flashcards_router.put("/{flashcard_id}", response_model=FlashcardResponse)
def update_flashcard(
    flashcard_id: int,
    flashcard_update: FlashcardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id, 
        Flashcard.user_id == current_user.id
    ).first()
    if not db_flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    db_flashcard.question = flashcard_update.question
    db_flashcard.answer = flashcard_update.answer
    db_flashcard.status = flashcard_update.status
    
    db.commit()
    db.refresh(db_flashcard)
    return db_flashcard

@flashcards_router.delete("/{flashcard_id}", status_code=204)
def delete_flashcard(
    flashcard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_flashcard = db.query(Flashcard).filter(
        Flashcard.id == flashcard_id, 
        Flashcard.user_id == current_user.id
    ).first()
    if not db_flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    db.delete(db_flashcard)
    db.commit()
    return


# Роутер для языков
languages_router = APIRouter(prefix="/languages", tags=["Languages"])

@languages_router.post("", response_model=LanguageResponse, status_code=201)
def create_language(language: LanguageCreate, db: Session = Depends(get_db)):
    existing_language = db.query(Languages).filter(Languages.code == language.code).first()

    if existing_language:
        return existing_language

    new_language = Languages(code=language.code)
    db.add(new_language)
    db.commit()
    db.refresh(new_language)
    return new_language

@languages_router.get("", response_model=list[LanguageResponse])
def get_languages(db: Session = Depends(get_db)):
    languages = db.query(Languages).all()
    return languages


# Роутер для AI 

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

chat_router = APIRouter(prefix="/chat", tags=["Chat"])
@chat_router.post("/message")
async def chat_with_ai(
    request: AIMessageRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    message_text = request.message.lower()  # сразу в нижний регистр

    if "последние 5 флешкарт" in message_text:
        flashcards = (
            db.query(Flashcard)
            .filter(
                Flashcard.user_id == current_user.id,
                Flashcard.status != FlashcardStatusEnum.DONE  # исключаем изученные
            )
            .order_by(Flashcard.created_at.desc())
            .limit(5)
            .all()
        )

        if not flashcards:
            return {"response": "У тебя пока нет неизученных флешкарт 😅"}

        cards_text = "\n".join(
            [f"{f.topic or 'Без темы'} — {f.question}: {f.answer}" for f in flashcards]
        )
        return {"response": f"Вот твои последние 5 неизученных флешкарт:\n{cards_text}"}

    elif "все неизученные флешкарты" in message_text:
        flashcards = (
            db.query(Flashcard)
            .filter(
                Flashcard.user_id == current_user.id,
                Flashcard.status != FlashcardStatusEnum.DONE
            )
            .order_by(Flashcard.created_at.desc())
            .all()
        )

        if not flashcards:
            return {"response": "У тебя пока нет неизученных флешкарт 😅"}

        cards_text = "\n".join(
            [f"{f.topic or 'Без темы'} — {f.question}: {f.answer}" for f in flashcards]
        )
        return {"response": f"Вот все твои неизученные флешкарты:\n{cards_text}"}

    elif "изученные флешкарты" in message_text.lower():
        flashcards = (
            db.query(Flashcard)
            .filter(
                Flashcard.user_id == current_user.id,
                Flashcard.status == FlashcardStatusEnum.DONE  # <- именно значение enum
            )
            .order_by(Flashcard.created_at.desc())
            .all()
        )
        
        if not flashcards:
            return {"response": "У тебя пока нет изученных флешкарт 😅"}

        cards_text = "\n".join(
            [f"{f.topic or 'Без темы'} — {f.question}: {f.answer}" for f in flashcards]
        )
        return {"response": f"Вот твои изученные флешкарты:\n{cards_text}"}

    # Остальные сообщения отправляем в Gemini
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(request.message)
        return {"response": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== Подключение роутеров ==========
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(flashcards_router)
app.include_router(languages_router)
app.include_router(chat_router)


# ========== Главная страница ==========
@app.get("/")
def read_root():
    return {"message": "Привет, Солнышко!"}