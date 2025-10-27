from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import openai
import base64
import os

app = FastAPI()

@app.post("/describe-image/")
def describe_image(
    question: str = Form(...),
    image: UploadFile = File(...)
):
    image_bytes = image.file.read()
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                ]}
            ],
            max_tokens=512
        )
        return {"answer": response.choices[0].message.content}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
