from fastapi import FastAPI

app = FastAPI(title="TMDB RecSys API")


@app.get("/health")
def health():
    return {"status": "ok"}
