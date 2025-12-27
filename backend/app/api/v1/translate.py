"""
Translation API Routes
翻译相关接口
"""

import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_effective_config
from app.core.database import get_db
from app.models.prompt import PromptTemplate
from app.models.translation import DictionaryHistory, TextTranslation
from app.models.user import User
from app.schemas.translation import (
    AddToVocabularyRequest,
    DictionaryResponse,
    TextTranslateRequest,
    TextTranslateResponse,
    TextTranslationHistory,
    TTSRequest,
    VocabularyItem,
)
from app.services.llm_service import get_llm_service
from app.services.tts_service import TTSService, get_tts_service

router = APIRouter(prefix="/translate", tags=["Translation"])


@router.post("/text", response_model=TextTranslateResponse)
async def translate_text(
    request: TextTranslateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Translate text"""
    # Get effective config (admin's config if can_use_admin_key=true)
    config = await get_effective_config(current_user, db)

    # Get LLM service
    llm = await get_llm_service(config)

    # fetch custom prompt
    stmt = select(PromptTemplate).where(
        PromptTemplate.user_id == current_user.id,
        PromptTemplate.template_type == "translation",
        PromptTemplate.is_active == True,
    )
    result = await db.execute(stmt)
    active_prompt = result.scalar_one_or_none()

    try:
        translated = await llm.translate(
            text=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            style=request.style,
            custom_prompt=active_prompt.content if active_prompt else None,
        )

        # Save to history
        history = TextTranslation(
            user_id=current_user.id,
            source_text=request.text,
            translated_text=translated,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            llm_model=llm.model,
        )
        db.add(history)
        await db.commit()

        return TextTranslateResponse(
            original_text=request.text,
            translated_text=translated,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            llm_model=llm.model,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@router.post("/text/stream")
async def translate_text_stream(
    request: TextTranslateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Translate text with streaming response"""
    config = await get_effective_config(current_user, db)

    llm = await get_llm_service(config)

    # fetch custom prompt
    stmt = select(PromptTemplate).where(
        PromptTemplate.user_id == current_user.id,
        PromptTemplate.template_type == "translation",
        PromptTemplate.is_active == True,
    )
    result = await db.execute(stmt)
    active_prompt = result.scalar_one_or_none()

    async def generate():
        try:
            async for chunk in llm.translate_stream(
                text=request.text,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                custom_prompt=active_prompt.content if active_prompt else None,
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/history", response_model=list[TextTranslationHistory])
async def get_translation_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get translation history"""
    result = await db.execute(
        select(TextTranslation)
        .where(TextTranslation.user_id == current_user.id)
        .order_by(TextTranslation.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ========== Dictionary ==========


@router.get("/dictionary/history", response_model=list[str])
async def get_dictionary_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent dictionary lookups"""
    # Use subquery to get the most recent lookup time for each word
    from sqlalchemy import func

    subquery = (
        select(DictionaryHistory.word, func.max(DictionaryHistory.created_at).label("last_lookup"))
        .where(DictionaryHistory.user_id == current_user.id)
        .group_by(DictionaryHistory.word)
        .subquery()
    )

    result = await db.execute(
        select(subquery.c.word).order_by(subquery.c.last_lookup.desc()).limit(limit)
    )
    return [row[0] for row in result.all()]


@router.get("/dictionary/{word}", response_model=DictionaryResponse)
async def lookup_word(
    word: str,
    language: str = "en",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Look up word in dictionary"""
    config = await get_effective_config(current_user, db)

    # Save to history
    history = DictionaryHistory(user_id=current_user.id, word=word, language=language)
    db.add(history)

    # Use LLM for dictionary lookup
    llm = await get_llm_service(config)

    # fetch custom prompt
    stmt = select(PromptTemplate).where(
        PromptTemplate.user_id == current_user.id,
        PromptTemplate.template_type == "dictionary",
        PromptTemplate.is_active == True,
    )
    result = await db.execute(stmt)
    active_prompt = result.scalar_one_or_none()

    try:
        result = await llm.lookup_word(
            word, language, custom_prompt=active_prompt.content if active_prompt else None
        )
        await db.commit()
        return DictionaryResponse(**result)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Dictionary lookup failed: {str(e)}")


@router.get("/vocabulary", response_model=list[VocabularyItem])
async def get_vocabulary(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get user's vocabulary book"""
    result = await db.execute(
        select(DictionaryHistory)
        .where(
            DictionaryHistory.user_id == current_user.id, DictionaryHistory.is_in_vocabulary == True
        )
        .order_by(DictionaryHistory.created_at.desc())
    )
    return result.scalars().all()


@router.post("/vocabulary")
async def add_to_vocabulary(
    request: AddToVocabularyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add word to vocabulary book"""
    # Check if already in vocabulary
    result = await db.execute(
        select(DictionaryHistory).where(
            DictionaryHistory.user_id == current_user.id,
            DictionaryHistory.word == request.word,
            DictionaryHistory.is_in_vocabulary == True,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        return {"message": "Word already in vocabulary"}

    # Add new entry
    entry = DictionaryHistory(
        user_id=current_user.id, word=request.word, language=request.language, is_in_vocabulary=True
    )
    db.add(entry)
    await db.commit()

    return {"message": "Word added to vocabulary"}


@router.delete("/vocabulary/{word}")
async def remove_from_vocabulary(
    word: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Remove word from vocabulary book"""
    result = await db.execute(
        select(DictionaryHistory).where(
            DictionaryHistory.user_id == current_user.id,
            DictionaryHistory.word == word,
            DictionaryHistory.is_in_vocabulary == True,
        )
    )
    entry = result.scalar_one_or_none()

    if entry:
        entry.is_in_vocabulary = False
        await db.commit()

    return {"message": "Word removed from vocabulary"}


# ========== TTS ==========


@router.post("/tts")
async def text_to_speech(
    request: TTSRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to speech"""
    config = await get_effective_config(current_user, db)

    tts = await get_tts_service(config)

    try:
        audio_data = await tts.synthesize(
            text=request.text, voice=request.voice, speed=request.speed
        )

        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")


@router.get("/tts/voices")
async def get_tts_voices():
    """Get available TTS voices"""
    return TTSService.get_available_voices()
