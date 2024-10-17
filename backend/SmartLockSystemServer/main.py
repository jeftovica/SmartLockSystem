from fastapi import FastAPI

from routers.user_router import user_router

app = FastAPI()
app.include_router(user_router)


