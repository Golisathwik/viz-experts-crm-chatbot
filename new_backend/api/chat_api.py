from fastapi import APIRouter, Depends, Form, File, UploadFile
from typing import Optional

from new_backend.auth.dependencies import get_current_user_id
from new_backend.controllers.conversation_controller import ConversationController
from new_backend.repositories.chat_repository import ChatRepository
from new_backend.repositories.config_repository import ConfigRepository
from new_backend.services.crm_service import CRMService

router = APIRouter()

controller = ConversationController()


@router.post("/chat")
async def chat(

    session_id: int = Form(...),

    prompt: str = Form(...),

    file: Optional[UploadFile] = File(None),

    user_id: int = Depends(get_current_user_id),

):

    config = ConfigRepository.get_config(user_id)

    if not config:

        return {

            "success": False,

            "message": "Configuration not found."

        }

    history = ChatRepository.get_chat_messages(session_id)

    file_context = ""

    if file:

        file_context = await file.read()
        
    crm_service = CRMService(
        user_id=user_id
    )
    api_keys = {
        "groq": config.get("groq_api_key"),
        "gemini": config.get("gemini_api_key"),
    }

    result = await controller.process_message(
        crm_service=crm_service,
        user_id=user_id,
        session_id=session_id,
        prompt=prompt,
        history=history,
        file_context=file_context,
        api_keys=api_keys,
    )

    return result