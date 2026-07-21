from fastapi import APIRouter, Depends, HTTPException, Request
from users.models import user_model
from database_config import SessionDep
from database_schema import users
from sqlalchemy.exc import IntegrityError
from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone
from config import settings
import jwt
from auth.current_user_extraction import get_current_user

router = APIRouter(prefix="/users", tags=['users'])
@router.post('/register', status_code = 201)
async def createUser(requestData: user_model.UserModel, session: SessionDep):
    try:
        hashedPasword = PasswordHash.recommended().hash(requestData.password)
        user = users(id = requestData.user_name, password = hashedPasword)
        session.add(user)
        session.commit()
        return {"message": "user created"}
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code = 409, detail = "username already exists")


@router.post('/login', status_code = 200)
async def login(requestData: user_model.UserModel, session: SessionDep):
    id = requestData.user_name
    user =  session.get(users, id)
    if not user:
        raise HTTPException(status_code = 400, detail = "wrong credentials")
    else:
        if PasswordHash.recommended().verify(requestData.password, user.password):
            to_encode = {
                "sub": requestData.user_name,
                "exp": datetime.now(timezone.utc) + timedelta(minutes = settings.jwt_token_expiry)
            }
            access_token = jwt.encode(to_encode, settings.jwt_secret, algorithm = settings.jwt_algorithm)
            return {
                "message": "login success",
                "access_token": access_token,
                "token_type": "bearer"
            }
        else:
            raise HTTPException(status_code = 400, detail = "wrong credentials")
        

@router.delete('/unregister', status_code = 200)
async def deleteUser(session: SessionDep, currentUser: str = Depends(get_current_user)):
    id = currentUser
    user = session.get(users, id)
    if not user:
        raise HTTPException(status_code = 404, detail = "user not exists")
    else:
        session.delete(user)
        session.commit()
        return {"message": "user deleted"}


@router.post('/verify', status_code = 200)
async def verifyUser():
    return await get_current_user()


