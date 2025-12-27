"""
Prompt Templates API
API for managing custom prompt templates
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.prompt import PromptTemplate
from app.models.user import User
from app.schemas.prompt import (
    PromptTemplateCreate,
    PromptTemplateResponse,
    PromptTemplateUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[PromptTemplateResponse])
async def list_prompts(
    template_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all prompt templates for the current user"""
    query = select(PromptTemplate).where(PromptTemplate.user_id == current_user.id)

    if template_type:
        query = query.where(PromptTemplate.template_type == template_type)

    # Order by template_type then created_at desc
    query = query.order_by(PromptTemplate.template_type, PromptTemplate.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    prompt_data: PromptTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new prompt template"""
    # If this is marked as active, unset other active prompts of same type
    if prompt_data.is_active:
        await db.execute(
            update(PromptTemplate)
            .where(
                PromptTemplate.user_id == current_user.id,
                PromptTemplate.template_type == prompt_data.template_type,
            )
            .values(is_active=False)
        )

    db_prompt = PromptTemplate(
        user_id=current_user.id,
        name=prompt_data.name,
        template_type=prompt_data.template_type,
        content=prompt_data.content,
        is_active=prompt_data.is_active,
    )
    db.add(db_prompt)
    await db.commit()
    await db.refresh(db_prompt)
    return db_prompt


@router.put("/{prompt_id}", response_model=PromptTemplateResponse)
async def update_prompt(
    prompt_id: UUID,
    prompt_data: PromptTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a prompt template"""
    query = select(PromptTemplate).where(
        PromptTemplate.id == prompt_id, PromptTemplate.user_id == current_user.id
    )
    result = await db.execute(query)
    db_prompt = result.scalar_one_or_none()

    if not db_prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prompt template not found"
        )

    update_data = prompt_data.model_dump(exclude_unset=True)

    # Handle is_active exclusivity
    if update_data.get("is_active") and not db_prompt.is_active:
        target_type = update_data.get("template_type", db_prompt.template_type)
        await db.execute(
            update(PromptTemplate)
            .where(
                PromptTemplate.user_id == current_user.id,
                PromptTemplate.template_type == target_type,
            )
            .values(is_active=False)
        )

    for field, value in update_data.items():
        setattr(db_prompt, field, value)

    await db.commit()
    await db.refresh(db_prompt)
    return db_prompt


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a prompt template"""
    # Check if exists
    query = select(PromptTemplate).where(
        PromptTemplate.id == prompt_id, PromptTemplate.user_id == current_user.id
    )
    result = await db.execute(query)
    db_prompt = result.scalar_one_or_none()

    if not db_prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prompt template not found"
        )

    await db.delete(db_prompt)
    await db.commit()
