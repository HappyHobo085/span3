from fastapi import FastAPI
from database import engine
import models

# Skep alle tabelle outomaties by opstart
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Backend is working"}