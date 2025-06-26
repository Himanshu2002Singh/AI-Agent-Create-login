from fastapi import FastAPI
from pydantic import BaseModel
from bot import process_transaction_request

class TransactionRequest(BaseModel):
    url: str
    username: str
    amount: float
    type: str

app = FastAPI()

@app.post("/process")
async def process(data: TransactionRequest):
    result = process_transaction_request(data.dict())
    return result
