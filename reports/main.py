from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import asyncpg


access_token = {"user_id": 1}


class UserReport(BaseModel):
    user_id: int
    device_id: int
    action_count: int


DB_DSN = "postgresql://airflow:airflow@airflow_db:5432/sample"

async def get_connection():
    return await asyncpg.connect(DB_DSN)

router = APIRouter()

@router.get("/reports/{user_id}", response_model=List[UserReport])
async def get_report_by_user(user_id: int):
    if user_id != access_token["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    conn = await get_connection()
    try:
        rows = await conn.fetch(
            "SELECT user_id, device_id, action_count FROM user_report WHERE user_id = $1",
            user_id
        )
    finally:
        await conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No data found")

    return [dict(row) for row in rows]


app = FastAPI()
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)