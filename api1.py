from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from core1 import process_user_bot

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ClientRequest(BaseModel):
    client_username: str
    weburl: str

@app.post("/create-client/")
def create_client(data: ClientRequest):
    result = process_user_bot(data.client_username, data.weburl)
    if result:
        return result
    raise HTTPException(status_code=404, detail="User creation failed or domain not found.")
