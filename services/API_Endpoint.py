from fastapi import FastAPI, Body
from sqlalchemy.orm import Session
from feedback import Feedback, SessionLocal

app = FastAPI()

@app.post("/feedback")
async def log_feedback(call_id: str = Body(...),
                       response: str = Body(...),
                       rating: int = Body(...)):
    db: Session = SessionLocal()
    fb = Feedback(call_id=call_id, response=response, rating=rating)
    db.add(fb)
    db.commit()
    db.close()
    return {"status": "recorded"}
