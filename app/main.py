import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import asyncio
from contextlib import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request
from starlette import status
from app.info.db_info import init_db
from app.routers import specific
from app.routers import user_acess
from app.routers import admin_access
from app.routers import end_chat
from app.components import heartbeat
from app.middleware import ValidationExceptionMiddleware
from app.logger import logging

 
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown logic."""
    init_db()
    heartbeat.stop_event.clear()
    task1 = asyncio.create_task(heartbeat.cleanup_inactive_sessions())
    task2 = asyncio.create_task(heartbeat.periodic_cleanup_old_data())  # Start cleanup task
    try:
        yield  # The app runs while this yields
    finally:
        heartbeat.stop_event.set()
        task1.cancel()  # Ensure cleanup task stops on shutdown
        task2.cancel()
        try:
            await asyncio.gather(task1, task2, return_exceptions=True)

        except asyncio.CancelledError:
            logging.info("Cleanup task cancelled.")
 
 
app = FastAPI(lifespan=lifespan)

app.include_router(specific.router, prefix='/report')
app.include_router(user_acess.router, prefix='/user_acess')
app.include_router(end_chat.router)

app.add_middleware(SessionMiddleware, secret_key="secret_key")
app.add_middleware(ValidationExceptionMiddleware)
 

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logging.error(f"A bad request error in endpoint [{request.url.path}] with error as [{exc.errors}]")    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
             "message": "Bad Request - Invalid input",
             "error":True,
             "data": []
                }
            )


if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host='0.0.0.0',
        port=8000,
        reload=True
        )
