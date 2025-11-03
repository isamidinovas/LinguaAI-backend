from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db, Base, engine
from app.models import User
from app.schemas import UserSignup

# Создать таблицы, если их нет
Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Привет, Солнышко!"}

@app.post("/signup")
def signup(user: UserSignup, db: Session = Depends(get_db)):
    # Проверка, существует ли email
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Сохранить пользователя (⚠️ пароль лучше хэшировать!)
    new_user = User(
        full_name=user.full_name,
        email=user.email,
        password=user.password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "message": "User registered successfully",
        "user": {"full_name": new_user.full_name, "email": new_user.email}
    }


@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users