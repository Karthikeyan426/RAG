from fastapi import FastAPI
from chats import chat_api
from users import users_api
from docs import docs_api
from database_config import lifespan
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(lifespan = lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/')
async def root():
    return 'server running'

app.include_router(chat_api.router)
app.include_router(users_api.router)
app.include_router(docs_api.router)
