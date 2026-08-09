from fastapi import APIRouter, Depends, HTTPException

from new_backend.auth.dependencies import get_current_user_id
from new_backend.repositories.chat_repository import ChatRepository

router = APIRouter(
    prefix="/sessions",
    tags=["Sessions"],
)


@router.get("")
def get_sessions(
    user_id: int = Depends(get_current_user_id),
):
    return ChatRepository.get_chat_sessions(user_id)


@router.post("/new")
def create_session(
    title: str = "New Chat",
    user_id: int = Depends(get_current_user_id),
):
    session_id = ChatRepository.create_chat_session(
        user_id=user_id,
        title=title,
    )

    return {
        "success": True,
        "session_id": session_id,
        "title": title
    }


@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
):
    session = ChatRepository.get_chat_session(session_id)

    if not session:
        raise HTTPException(404, "Session not found")

    if session["user_id"] != user_id:
        raise HTTPException(403, "Forbidden")

    ChatRepository.delete_chat_session(session_id)
    return {
        "success": True,
        "message": "Session deleted successfully",
    }


@router.delete("")
def delete_all_sessions(
    user_id: int = Depends(get_current_user_id),
):
    ChatRepository.delete_all_chat_sessions(user_id)

    return {
        "success": True,
        "message": "All sessions deleted successfully",
    }
    
@router.get("/{session_id}")
def get_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
):
    session = ChatRepository.get_chat_session(session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    if session["user_id"] != user_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    messages = ChatRepository.get_chat_messages(session_id)

    return {
        "success": True,
        "id": session_id,
        "title": session["title"],
        "messages": messages
    }