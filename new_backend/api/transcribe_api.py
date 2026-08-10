from fastapi import APIRouter, Depends, UploadFile, File
from groq import Groq

from new_backend.auth.dependencies import get_current_user_id
from new_backend.repositories.config_repository import ConfigRepository


router = APIRouter()


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
):
    # ----------------------------------------------------------
    # Get the current user's saved API configuration
    # ----------------------------------------------------------

    config = ConfigRepository.get_config(user_id)

    if not config:
        return {
            "success": False,
            "text": "",
            "message": "Configuration not found."
        }


    # ----------------------------------------------------------
    # Use the Groq API key entered by this user
    # ----------------------------------------------------------

    groq_api_key = config.get("groq_api_key")

    if not groq_api_key:
        return {
            "success": False,
            "text": "",
            "message": "Groq API key is not configured."
        }


    # ----------------------------------------------------------
    # Read the recorded audio
    # ----------------------------------------------------------

    audio_data = await file.read()

    if not audio_data:
        return {
            "success": False,
            "text": "",
            "message": "The recorded audio is empty."
        }


    # ----------------------------------------------------------
    # Send audio to Groq Whisper
    # ----------------------------------------------------------

    try:

        client = Groq(
            api_key=groq_api_key
        )

        transcription = client.audio.transcriptions.create(
            file=(
                file.filename or "recording.webm",
                audio_data,
                file.content_type or "audio/webm"
            ),
            model="whisper-large-v3",
            response_format="json",
        )


        text = getattr(
            transcription,
            "text",
            ""
        ) or ""


        return {
            "success": True,
            "text": text.strip(),
        }


    except Exception as exc:

        print(
            f"Groq transcription error: {exc}"
        )

        return {
            "success": False,
            "text": "",
            "message": "Unable to transcribe the audio."
        }