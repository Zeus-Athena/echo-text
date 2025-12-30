"""
User API Routes
用户相关接口
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user, get_current_user
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password
from app.core.stt_model_registry import is_true_streaming as _is_true_streaming
from app.models.user import User, UserConfig
from app.schemas.user import (
    AdminCreateUser,
    AdminUpdateUser,
    DictConfig,
    LLMConfig,
    PasswordChange,
    PreferencesConfig,
    RecordingConfig,
    STTConfig,
    TTSConfig,
    UserConfigResponse,
    UserConfigUpdate,
    UserResponse,
    UserUpdate,
)

# trigger ci
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user information"""
    if user_data.username:
        current_user.username = user_data.username
    if user_data.email:
        # Check if email is already taken
        result = await db.execute(
            select(User).where(User.email == user_data.email, User.id != current_user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already taken"
            )
        current_user.email = user_data.email

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/me/password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change current user's password"""
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password"
        )

    current_user.password_hash = get_password_hash(password_data.new_password)
    await db.commit()

    return {"message": "Password updated successfully"}


# ========== User Config ==========


@router.get("/me/config", response_model=UserConfigResponse)
async def get_user_config(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get current user's configuration"""
    result = await db.execute(select(UserConfig).where(UserConfig.user_id == current_user.id))
    config = result.scalar_one_or_none()

    if not config:
        # Create default config
        config = UserConfig(user_id=current_user.id)
        db.add(config)
        await db.commit()
        await db.refresh(config)

    # Check if user can use admin's API keys
    using_admin_key = False
    api_config = config  # Default to user's own config

    if current_user.can_use_admin_key and current_user.role != "admin":
        # Find an admin user and use their config for API keys
        admin_result = await db.execute(select(User).where(User.role == "admin").limit(1))
        admin_user = admin_result.scalar_one_or_none()

        if admin_user:
            admin_config_result = await db.execute(
                select(UserConfig).where(UserConfig.user_id == admin_user.id)
            )
            admin_config = admin_config_result.scalar_one_or_none()
            if admin_config:
                api_config = admin_config
                using_admin_key = True

    # Determine active LLM key
    active_llm_key = api_config.llm_api_key
    if api_config.llm_provider and api_config.llm_provider.lower() == "groq":
        active_llm_key = api_config.llm_groq_api_key
    elif api_config.llm_provider and api_config.llm_provider.lower() == "siliconflow":
        active_llm_key = api_config.llm_siliconflow_api_key
    elif api_config.llm_provider and api_config.llm_provider.lower() == "siliconflowglobal":
        active_llm_key = api_config.llm_siliconflowglobal_api_key
    elif api_config.llm_provider and api_config.llm_provider.lower() == "fireworks":
        active_llm_key = api_config.llm_fireworks_api_key

    # Determine active STT key
    active_stt_key = api_config.stt_api_key
    if api_config.stt_provider:
        p = api_config.stt_provider.lower()
        if p == "groq":
            active_stt_key = api_config.stt_groq_api_key
        elif p == "deepgram":
            active_stt_key = api_config.stt_deepgram_api_key
        elif p == "openai":
            active_stt_key = api_config.stt_openai_api_key
        elif p == "siliconflow":
            active_stt_key = api_config.stt_siliconflow_api_key

    # Helper function to mask key
    def mask_key(key):
        return "***" if key else None

    # Parse URLs JSON
    import json

    def parse_urls(urls_json: str | None) -> dict:
        if not urls_json:
            return {}
        try:
            return json.loads(urls_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    return UserConfigResponse(
        llm=LLMConfig(
            provider=api_config.llm_provider,
            api_key=mask_key(active_llm_key),
            base_url=api_config.llm_base_url,
            model=api_config.llm_model,
            keys={
                "groq": mask_key(api_config.llm_groq_api_key),
                "siliconflow": mask_key(api_config.llm_siliconflow_api_key),
                "siliconflowglobal": mask_key(api_config.llm_siliconflowglobal_api_key),
                "fireworks": mask_key(api_config.llm_fireworks_api_key),
            },
            urls=parse_urls(api_config.llm_urls),
        ),
        stt=STTConfig(
            provider=api_config.stt_provider,
            api_key=mask_key(active_stt_key),
            base_url=api_config.stt_base_url,
            model=api_config.stt_model,
            keys={
                "groq": mask_key(api_config.stt_groq_api_key),
                "deepgram": mask_key(api_config.stt_deepgram_api_key),
                "openai": mask_key(api_config.stt_openai_api_key),
                "siliconflow": mask_key(api_config.stt_siliconflow_api_key),
            },
            urls=parse_urls(api_config.stt_urls),
            is_true_streaming=_is_true_streaming(api_config.stt_provider, api_config.stt_model),
        ),
        tts=TTSConfig(
            provider=api_config.tts_provider,
            api_key="***" if api_config.tts_api_key else None,
            base_url=api_config.tts_base_url,
            voice=api_config.tts_voice,
            urls=parse_urls(api_config.tts_urls),
        ),
        dict=DictConfig(
            provider=api_config.dict_provider, api_key="***" if api_config.dict_api_key else None
        ),
        preferences=PreferencesConfig(
            theme=config.theme,  # Use user's own preferences
            default_source_lang=config.default_source_lang,
            default_target_lang=config.default_target_lang,
        ),
        recording=RecordingConfig(
            audio_buffer_duration=config.audio_buffer_duration,
            silence_threshold=config.silence_threshold,
            silence_mode=config.silence_mode,
            silence_prefer_source=config.silence_prefer_source,
            silence_threshold_source=config.silence_threshold_source,
            translation_mode=config.translation_mode,
            segment_soft_threshold=config.segment_soft_threshold,
            segment_hard_threshold=config.segment_hard_threshold,
        ),
        using_admin_key=using_admin_key,
    )


@router.put("/me/config", response_model=UserConfigResponse)
async def update_user_config(
    config_data: UserConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's configuration"""
    result = await db.execute(select(UserConfig).where(UserConfig.user_id == current_user.id))
    config = result.scalar_one_or_none()

    if not config:
        config = UserConfig(user_id=current_user.id)
        db.add(config)

    # Update LLM config
    if config_data.llm:
        if config_data.llm.provider is not None:
            config.llm_provider = config_data.llm.provider
        if config_data.llm.api_key is not None and config_data.llm.api_key != "***":
            # For backward compatibility or valid simple updates
            config.llm_api_key = config_data.llm.api_key

            # Also update specific key if provider is known
            if config.llm_provider:
                p = config.llm_provider.lower()
                if p == "groq":
                    config.llm_groq_api_key = config_data.llm.api_key
                elif p == "siliconflow":
                    config.llm_siliconflow_api_key = config_data.llm.api_key
                elif p == "siliconflowglobal":
                    config.llm_siliconflowglobal_api_key = config_data.llm.api_key
                elif p == "fireworks":
                    config.llm_fireworks_api_key = config_data.llm.api_key

        if config_data.llm.base_url is not None:
            config.llm_base_url = config_data.llm.base_url
        if config_data.llm.model is not None:
            config.llm_model = config_data.llm.model

        # Update specific keys
        if config_data.llm.keys:
            if "groq" in config_data.llm.keys:
                key = config_data.llm.keys["groq"]
                if key is not None and key != "***":
                    config.llm_groq_api_key = key
            if "siliconflow" in config_data.llm.keys:
                key = config_data.llm.keys["siliconflow"]
                if key is not None and key != "***":
                    config.llm_siliconflow_api_key = key
            if "siliconflowglobal" in config_data.llm.keys:
                key = config_data.llm.keys["siliconflowglobal"]
                if key is not None and key != "***":
                    config.llm_siliconflowglobal_api_key = key
            if "fireworks" in config_data.llm.keys:
                key = config_data.llm.keys["fireworks"]
                if key is not None and key != "***":
                    config.llm_fireworks_api_key = key

        # Update LLM provider-specific URLs
        if config_data.llm.urls is not None:
            import json

            # Merge with existing URLs
            existing_urls = {}
            if config.llm_urls:
                try:
                    existing_urls = json.loads(config.llm_urls)
                except (json.JSONDecodeError, TypeError):
                    pass
            # Update with new values
            for provider, url in config_data.llm.urls.items():
                existing_urls[provider] = url
            config.llm_urls = json.dumps(existing_urls)

    # Update STT config
    if config_data.stt:
        from loguru import logger

        logger.info(
            f"STT Config Save: provider={config_data.stt.provider}, base_url={config_data.stt.base_url}, model={config_data.stt.model}"
        )
        if config_data.stt.provider is not None:
            logger.info(
                f"Updating stt_provider from {config.stt_provider} to {config_data.stt.provider}"
            )
            config.stt_provider = config_data.stt.provider
        if config_data.stt.api_key is not None and config_data.stt.api_key != "***":
            config.stt_api_key = config_data.stt.api_key

            # Also update specific key
            if config.stt_provider:
                p = config.stt_provider.lower()
                if p == "groq":
                    config.stt_groq_api_key = config_data.stt.api_key
                elif p == "deepgram":
                    config.stt_deepgram_api_key = config_data.stt.api_key
                elif p == "openai":
                    config.stt_openai_api_key = config_data.stt.api_key
                elif p == "siliconflow":
                    config.stt_siliconflow_api_key = config_data.stt.api_key

        if config_data.stt.base_url is not None:
            config.stt_base_url = config_data.stt.base_url
        if config_data.stt.model is not None:
            config.stt_model = config_data.stt.model

        # Update specific keys
        if config_data.stt.keys:
            if "groq" in config_data.stt.keys:
                key = config_data.stt.keys["groq"]
                if key is not None and key != "***":
                    config.stt_groq_api_key = key
            if "deepgram" in config_data.stt.keys:
                key = config_data.stt.keys["deepgram"]
                if key is not None and key != "***":
                    config.stt_deepgram_api_key = key
            if "openai" in config_data.stt.keys:
                key = config_data.stt.keys["openai"]
                if key is not None and key != "***":
                    config.stt_openai_api_key = key
            if "siliconflow" in config_data.stt.keys:
                key = config_data.stt.keys["siliconflow"]
                if key is not None and key != "***":
                    config.stt_siliconflow_api_key = key

        # Update STT provider-specific URLs
        if config_data.stt.urls is not None:
            import json

            existing_urls = {}
            if config.stt_urls:
                try:
                    existing_urls = json.loads(config.stt_urls)
                except (json.JSONDecodeError, TypeError):
                    pass
            for provider, url in config_data.stt.urls.items():
                existing_urls[provider] = url
            config.stt_urls = json.dumps(existing_urls)

    # Update TTS config
    if config_data.tts:
        if config_data.tts.provider is not None:
            config.tts_provider = config_data.tts.provider
        if config_data.tts.api_key is not None and config_data.tts.api_key != "***":
            config.tts_api_key = config_data.tts.api_key
        if config_data.tts.voice is not None:
            config.tts_voice = config_data.tts.voice

        # Update TTS provider-specific URLs
        if config_data.tts.urls is not None:
            import json

            existing_urls = {}
            if config.tts_urls:
                try:
                    existing_urls = json.loads(config.tts_urls)
                except (json.JSONDecodeError, TypeError):
                    pass
            for provider, url in config_data.tts.urls.items():
                existing_urls[provider] = url
            config.tts_urls = json.dumps(existing_urls)

    # Update Dict config
    if config_data.dict:
        if config_data.dict.provider is not None:
            config.dict_provider = config_data.dict.provider
        if config_data.dict.api_key is not None and config_data.dict.api_key != "***":
            config.dict_api_key = config_data.dict.api_key

    # Update Preferences
    if config_data.preferences:
        if config_data.preferences.theme is not None:
            config.theme = config_data.preferences.theme
        if config_data.preferences.default_source_lang is not None:
            config.default_source_lang = config_data.preferences.default_source_lang
        if config_data.preferences.default_target_lang is not None:
            config.default_target_lang = config_data.preferences.default_target_lang

    # Update Recording config
    if config_data.recording:
        if config_data.recording.audio_buffer_duration is not None:
            config.audio_buffer_duration = config_data.recording.audio_buffer_duration
        if config_data.recording.silence_threshold is not None:
            config.silence_threshold = config_data.recording.silence_threshold
        if config_data.recording.silence_mode is not None:
            config.silence_mode = config_data.recording.silence_mode
        if config_data.recording.silence_prefer_source is not None:
            config.silence_prefer_source = config_data.recording.silence_prefer_source
        if config_data.recording.silence_threshold_source is not None:
            config.silence_threshold_source = config_data.recording.silence_threshold_source
        if config_data.recording.translation_mode is not None:
            config.translation_mode = config_data.recording.translation_mode
        if config_data.recording.segment_soft_threshold is not None:
            config.segment_soft_threshold = config_data.recording.segment_soft_threshold
        if config_data.recording.segment_hard_threshold is not None:
            config.segment_hard_threshold = config_data.recording.segment_hard_threshold

    await db.commit()
    await db.refresh(config)

    # Return updated config (call get_user_config logic)
    return await get_user_config(current_user, db)


@router.get("/me/balance")
async def check_balance(
    service_type: str = "llm",
    provider: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check account balance for LLM or STT provider.

    Args:
        service_type: "llm" or "stt"
        provider: Optional provider name to override user config
    """
    if service_type not in ("llm", "stt"):
        raise HTTPException(status_code=400, detail="service_type must be 'llm' or 'stt'")

    # Get user config
    result = await db.execute(select(UserConfig).where(UserConfig.user_id == current_user.id))
    user_config = result.scalar_one_or_none()

    if not user_config:
        return {"error": "User config not found"}

    # IMPORTANT: If provider is specified, we need to temporarily override WITHOUT persisting to DB
    # Use db.expunge() to detach the object from the session before modifying
    if provider:
        db.expunge(user_config)  # Detach from session to prevent accidental persistence
        if service_type == "llm":
            user_config.llm_provider = provider
        else:
            user_config.stt_provider = provider

    if service_type == "llm":
        from app.services.llm_service import LLMService

        service = LLMService(user_config)
    else:
        from app.services.stt_service import STTService

        service = STTService(user_config)

    return await service.check_balance()


# ========== Admin Routes ==========


@router.get("/", response_model=list[UserResponse])
async def list_users(admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    """List all users (admin only)"""
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: AdminCreateUser,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user (admin only)"""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被注册")

    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")

    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        role="user",
        can_use_admin_key=user_data.can_use_admin_key,
    )
    db.add(user)
    await db.flush()

    # Create default config for user
    config = UserConfig(user_id=user.id)
    db.add(config)

    await db.commit()
    await db.refresh(user)

    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: AdminUpdateUser,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a user (admin only)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # Check if email already taken by another user
    if user_data.email and user_data.email != user.email:
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被使用")
        user.email = user_data.email

    # Check if username already taken by another user
    if user_data.username and user_data.username != user.username:
        result = await db.execute(select(User).where(User.username == user_data.username))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已被使用")
        user.username = user_data.username

    # Update password if provided
    if user_data.password:
        user.password_hash = get_password_hash(user_data.password)

    # Update can_use_admin_key if provided
    if user_data.can_use_admin_key is not None:
        user.can_use_admin_key = user_data.can_use_admin_key

    await db.commit()
    await db.refresh(user)

    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: str, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)
):
    """Delete a user and all related data (admin only)"""
    if str(admin.id) == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法删除自己的账户")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    await db.delete(user)
    await db.commit()

    return {"message": "用户已删除"}
