from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db, Base, engine
from app.models import User, Flashcard, Languages
from app.schemas import UserLogin, UserResponse, Token, FlashcardCreate, FlashcardResponse, UserWithFlashcardsResponse, FlashcardStatusEnum, LanguageResponse, LanguageCreate
from app.schemas import FlashcardsPaginatedResponse
from app.schemas import UserLogin,UserSignup, UserResponse, Token
from app.auth import verify_password, create_access_token
from fastapi.security import OAuth2PasswordBearer
from app.auth import get_password_hash
from app.auth import SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
from fastapi import status
from fastapi import Query

from sqlalchemy import or_
# Создать таблицы, если их нет
Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Привет, Солнышко!"}

@app.post("/register")
def signup(user: UserSignup, db: Session = Depends(get_db)):
    # Проверка, существует ли email
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Сохранить пользователя (⚠️ пароль лучше хэшировать!)
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




@app.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    # Ищем пользователя по full_name
    db_user = db.query(User).filter(User.full_name == user.full_name).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid full name or password")
    
    # Проверяем пароль
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid full name or password")
    
    # Создаём JWT-токен
    access_token = create_access_token({"sub": db_user.full_name})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
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


@app.get("/me", response_model=UserWithFlashcardsResponse)
def read_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Получаем флешкарты текущего пользователя
    flashcards = db.query(Flashcard).filter(Flashcard.user_id == current_user.id).all()
    
    # Возвращаем объект с вложенными флешкартами
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "flashcards": flashcards
    }



@app.post("/flashcards", response_model=FlashcardResponse, status_code=201)
def create_flashcard(
    flashcard: FlashcardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Ищем язык по коду
    language = db.query(Languages).filter_by(code=flashcard.language_code).first()
    if not language:
        raise HTTPException(status_code=404, detail="Language not found")
    
    # Создаём флешкарту с user_id и language_id
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




@app.get("/flashcards", response_model=FlashcardsPaginatedResponse)
def get_flashcards(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
):
    query = db.query(Flashcard)

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

@app.get("/flashcards/{flashcard_id}", response_model=FlashcardResponse)
def get_flashcard(
    flashcard_id: int,
    db: Session = Depends(get_db),
):
    db_flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
    if not db_flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    return db_flashcard

    
@app.get("/flashcards/statuses")
def get_flashcard_statuses():
    return [status.value for status in FlashcardStatusEnum]

@app.get("/flashcards/languages")
def get_flashcard_languages():
    return [lang.value for lang in LanguagesEnum]

@app.put("/flashcards/{flashcard_id}", response_model=FlashcardResponse)
def update_flashcard(
    flashcard_id: int,
    flashcard_update: FlashcardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id, Flashcard.user_id == current_user.id).first()
    if not db_flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    db_flashcard.question = flashcard_update.question
    db_flashcard.answer = flashcard_update.answer
    db_flashcard.status = flashcard_update.status
    
    db.commit()
    db.refresh(db_flashcard)
    return db_flashcard


@app.delete("/flashcards/{flashcard_id}", status_code=204)
def delete_flashcard(
    flashcard_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id, Flashcard.user_id == current_user.id).first()
    if not db_flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    
    db.delete(db_flashcard)
    db.commit()
    return  

@app.post("/languages", response_model=LanguageResponse, status_code=201)
def create_language(language: LanguageCreate, db: Session = Depends(get_db)):
    # language - это объект LanguageCreate, достаем строку
    existing_language = db.query(Languages).filter(Languages.code == language.code).first()

    if existing_language:
        return existing_language

    new_language = Languages(code=language.code, name=language.name)
    db.add(new_language)
    db.commit()
    db.refresh(new_language)
    return new_language
