from fastapi import FastAPI, Form, status, HTTPException, Depends, Request, Response, File, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from models import *
from database import engine
from sqlmodel import Session, select
from typing import Annotated
from typing import List
import bcrypt
import shutil


app = FastAPI()

templates = Jinja2Templates('templates')

session = Session(bind=engine)


@app.get('/', response_model=User, tags=['Pages'])
async def get_index_page(request: Request):

    cookie = request.cookies.get('id')
    flag = False

    if cookie != None:
        flag = True

    statement = select(advt)
    result = session.exec(statement).all()

    if result == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return templates.TemplateResponse(
        request=request,
        name='index.html',
        context={
            'result': result,
            'flag': flag,
            'user_id': cookie
        }
    )


@app.get('/login', tags=['Pages'])
async def get_login_page(request: Request):

    cookie = request.cookies.get('id')

    if cookie != None:
        return RedirectResponse('/profile/' + cookie, status_code=302)

    return templates.TemplateResponse('login.html', {'request': request})

@app.get('/registration', tags=['Pages'])
async def get_registration_page(request: Request):
    return templates.TemplateResponse('registration.html', {'request': request})

@app.get('/note/{advt_id}', tags=['Pages'])
async def get_note_page(request: Request, advt_id: int):

    cookie = request.cookies.get('id')
    flag = False

    if cookie != None:
        flag = True

    advt_statement = select(advt).where(advt.id == advt_id)
    advt_result = session.exec(advt_statement).first()

    statement = select(User).where(User.id == advt_result.user_id)
    result = session.exec(statement).first()

    return templates.TemplateResponse(
        request=request,
        name='note.html',
        context={
            'id': advt_result.id,
            'user_id': cookie,
            'title': advt_result.title,
            'desc': advt_result.desc,
            'result': result,
            'flag': flag
        }
    )

@app.get('/advt', tags=['Pages'])
async def get_advt_page(request: Request):

    cookie = request.cookies.get('id')
    flag = False

    if cookie != None:
        flag = True

    if cookie == None:
        return RedirectResponse('/login', status_code=302)

    return templates.TemplateResponse('advt.html', {'request': request}, context={
            'flag': flag
        })

@app.post('/advt', status_code=status.HTTP_201_CREATED,
          response_class=RedirectResponse)
async def create_advt(request: Request,
                      title: str = Form(...),
                      desc: str = Form(...)) -> RedirectResponse:

    cookie = request.cookies.get('id')
    new = advt(user_id = cookie, title = title, desc = desc)

    session.add(new)
    session.commit()

    return RedirectResponse('/note/' + str(new.id), status_code=302)

@app.get('/profile/{user_id}', response_model=User, tags=['Pages'])
async def get_profile_user(request: Request, user_id: int):

    note_statement = select(advt).where(advt.user_id == user_id)
    note_result = session.exec(note_statement).all()

    statement = select(User).where(User.id == user_id)
    result = session.exec(statement).first()

    if result == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return templates.TemplateResponse(
        request=request,
        user_id = user_id,
        name='profile.html',
        context={
            'note_result': note_result,
            'id': result.id,
            'name': result.name,
            'email': result.email,
            'password': result.password
        }
    )

@app.post('/registration', status_code=status.HTTP_201_CREATED,
          response_class=RedirectResponse, tags=['Account'])
async def create_a_user(name: str = Form(...),
                        email: str = Form(...),
                        password: str = Form(...),
                        remember: Optional[bool] = Form(default=False)) -> RedirectResponse:

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


    statement = select(User).where(User.email == email)
    result = session.exec(statement).one_or_none()

    new = User(name=name, email=email, password=hashed_password)

    if result == None:
        session.add(new)
        session.commit()
        session.rollback()

        response = RedirectResponse('/profile/' + str(new.id), status_code=302)
        response.delete_cookie('id')
        if remember == True:
            response.set_cookie(key="id", value=str(new.id), max_age=15695000)
        return response

    return RedirectResponse('/registration', status_code=302)

@app.post('/login', response_class=RedirectResponse, tags=['Account'])
async def get_user(email_login: str = Form(...),
                   password_login: str = Form(...),
                   remember: Optional[bool] = Form(default=False)) -> RedirectResponse:

    statement = select(User).where(User.email == email_login)
    result = session.exec(statement).first()

    if result and bcrypt.checkpw(password_login.encode('utf-8'), result.password.encode('utf-8')):
        response = RedirectResponse('/profile/' + str(result.id), status_code=302)
        if remember:
            response.set_cookie(key="id", value=str(result.id), max_age=15695000)
        return response


    return RedirectResponse('/login', status_code=302)

@app.get('/profile', tags=['Account'])
async def switch_account(response: Response):
    response = RedirectResponse('/login', status_code=302)
    response.delete_cookie('id')
    return response


@app.post('/upload1', tags=['Pages'])
async def upload_file(upload_file: UploadFile = File(...)):
    path = f'media/{upload_file.name}'
    with open(path,'wb+') as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return {
        'file': upload_file,
        'filename': upload_file.filename,
        'path': path,
        'type': upload_file.content_type
    }

@app.post('/upload2', tags=['Pages'])
async def upload_multiple_files(uploaded_files: List[UploadFile] = File(...)):
    res = []
    for uploaded_files in uploaded_files:
        path = f'media/{upload_file.name}'
        with open(path,'wb+') as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        res.append(upload_file)
    return res

## Для поиска файла: вбиваешь название файла - файл выводится

@app.get('/download/{file_name}', response_class=FileResponse, tags=['Pages'])
async def download_file(file_name: str):
    path = f'media/{file_name}'
    return path