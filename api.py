from fastapi import FastAPI

app = FastAPI(title="Clawback API")


@app.get("/")
def root():
    return {
        "name": "Clawback",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
