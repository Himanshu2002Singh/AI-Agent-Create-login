from fastapi import FastAPI
from pydantic import BaseModel
from core import process_user_bot

app = FastAPI()

class ClientData(BaseModel):
    client_username: str
    weburl: str

@app.post("/create-client")
def create_client(data: ClientData):
    result = process_user_bot(data.client_username, data.weburl)
    if result:
        return {"status": "success", "data": result}
    return {"status": "error", "message": "Failed to create client"}
