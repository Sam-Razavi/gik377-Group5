# Ansvarig: Nina Bentmosse
# Modul: Översättningstjänst

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from services.translation.service import TranslationService

router = APIRouter(prefix="/translation", tags=["translation"])
v3beta1_router = APIRouter(tags=["translation"])

translation_service = TranslationService()


class TranslateRequest(BaseModel):
    text: str
    target_language: str = "en"


class TranslateTextRequest(BaseModel):
    contents: List[str]
    targetLanguageCode: str
    sourceLanguageCode: Optional[str] = None
    mimeType: str = "text/plain"


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


@v3beta1_router.post("/v3beta1/projects/{project_id}:translateText")
def translate_text_v3beta1(project_id: str, body: TranslateTextRequest):
    """Google Cloud Translation API v3beta1-kompatibel endpoint.

    POST /v3beta1/{parent=projects/*}:translateText

    Body (JSON):
        contents            : list[str] — texterna som ska översättas
        targetLanguageCode  : str       — ISO-639-1 kod, t.ex. "sv", "en", "ja"
        sourceLanguageCode  : str       — (valfritt) källspråk
        mimeType            : str       — "text/plain" (standard) eller "text/html"
    """
    translations = []
    for content in body.contents:
        try:
            translated = translation_service.translate(content, target_language=body.targetLanguageCode)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        detected = translation_service.detect_language(content)
        translations.append({
            "translatedText": translated,
            "detectedLanguageCode": detected,
        })
    return {"translations": translations}
