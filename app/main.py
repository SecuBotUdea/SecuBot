from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="SecuBot",
    version="1.0.0",
)

@app.get('/health')
async def health_check():
    return JSONResponse(content={"status": "healthy"})

@app.get('/')
async def root():
    return {"message": "Welcome to SecuBot"}