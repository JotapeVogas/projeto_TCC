from app.main import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=5000,
        reload=True,
        workers=1
    )
