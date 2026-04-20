# Ansvarig: Nina Bentmosse
# Modul: Översättningstjänst

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.translation.service import TranslationService

router = APIRouter(prefix="/translation", tags=["translation"])

translation_service = TranslationService()


class TranslateRequest(BaseModel):
    text: str
    target_language: str = "en"


@router.get("/languages")
def get_languages():
    """Returnerar alla stödda språk."""
    return translation_service.supported_languages()


@router.post("/translate")
def translate(body: TranslateRequest):
    """Översätt text till valfritt språk.

    Body (JSON):
        text            : str — texten som ska översättas
        target_language : str — ISO-639-1 kod, t.ex. "sv", "ar", "ja" (standard: "en")
    """
    try:
        translated = translation_service.translate(body.text, target_language=body.target_language)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    detected = translation_service.detect_language(body.text)
    return {"translated_text": translated, "detected_language": detected}
