import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import webhooks, conversations
from database import init_db

init_db()

app = FastAPI(
    title="Yellow.ai Agent Inbox API",
    version="1.0.0",
    description="Multi-tenant support agent inbox with webhook ingestion and atomic claim locking."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(conversations.router)

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "yellow-agent-inbox"}

# Serve Frontend Dashboard
if os.path.exists("ui"):
    app.mount("/", StaticFiles(directory="ui", html=True), name="ui")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
