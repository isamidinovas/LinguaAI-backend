from pydantic import BaseModel, EmailStr, validator

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
    full_name: str
    email: EmailStr

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str