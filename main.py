from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
import os

app = FastAPI()

# Allow Vercel frontend to call this API
origins = [
    "https://my-tm-app.vercel.app/",  # replace this with your actual Vercel URL
    "http://localhost:3000/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, #origins,  # or ["*"] for testing, but not recommended for production
    allow_credentials=True,
    allow_methods=["*"],  # allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # allow all headers
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",  # ✅ This is correct if it's at the project root
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),  # use 8080 to align with fly.toml
        reload=False
    )
