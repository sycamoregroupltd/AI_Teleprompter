from fastapi import FastAPI, Body
from transformers import pipeline

app = FastAPI()
model_pipeline = pipeline("text-generation", model="gpt2")  # or another model

@app.post("/prompt")
async def prompt_ai(prompt: str = Body(...)):
    output = model_pipeline(prompt, max_length=50, num_return_sequences=1)
    return {"response": output[0]["generated_text"]}
