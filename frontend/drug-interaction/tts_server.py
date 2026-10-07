from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import edge_tts
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SpeechRequest(BaseModel):
    text: str
    language: str


VOICES = {
    "bn": "bn-IN-TanishaaNeural",
    "mr": "mr-IN-AarohiNeural"
}


@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "Regional TTS server is running"
    }


@app.post("/speak")
async def speak(request: SpeechRequest):

    voice = VOICES.get(request.language)

    if not voice:
        return {
            "error": "Unsupported language"
        }

    print("Received text:", request.text)
    print("Language:", request.language)
    print("Voice:", voice)

    communicate = edge_tts.Communicate(
        request.text,
        voice
    )

    audio = io.BytesIO()

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.write(chunk["data"])

    audio.seek(0)

    print("Audio generated successfully")

    return StreamingResponse(
        audio,
        media_type="audio/mpeg"
    )