"""
Large Object Storage Utilities
PostgreSQL Large Object for audio storage, with SQLite BLOB fallback

PostgreSQL Large Objects support:
- Streaming read/write
- Seeking (for HTTP Range requests)
- Up to 4TB per object
"""

import uuid

from loguru import logger
from sqlalchemy import LargeBinary, String, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.database import Base


class AudioBlob(Base):
    """SQLite fallback: Store audio as BLOB in table"""

    __tablename__ = "audio_blobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


def is_postgres() -> bool:
    """Check if using PostgreSQL"""
    return "postgresql" in settings.DATABASE_URL.lower()


async def save_audio_data(db: AsyncSession, audio_bytes: bytes) -> tuple[int | None, str | None]:
    """
    Save audio data to database.

    Returns:
        (oid, blob_id) - PostgreSQL returns (oid, None), SQLite returns (None, blob_id)
    """
    if is_postgres():
        return await _save_large_object(db, audio_bytes), None
    else:
        return None, await _save_blob(db, audio_bytes)


async def read_audio_data(
    db: AsyncSession,
    oid: int | None = None,
    blob_id: str | None = None,
    offset: int = 0,
    length: int = -1,
) -> bytes:
    """
    Read audio data from database with optional range.

    Args:
        db: Database session
        oid: PostgreSQL Large Object OID
        blob_id: SQLite blob ID
        offset: Start byte position
        length: Number of bytes to read (-1 for all)
    """
    if is_postgres() and oid:
        return await _read_large_object(db, oid, offset, length)
    elif blob_id:
        return await _read_blob(db, blob_id, offset, length)
    else:
        raise ValueError("Either oid or blob_id must be provided")


async def stream_audio_chunks(
    db: AsyncSession,
    oid: int | None = None,
    blob_id: str | None = None,
    chunk_size: int = 512 * 1024,
):
    """
    Generator to stream audio data in chunks.

    Args:
        db: Database session
        oid: PostgreSQL Large Object OID
        blob_id: SQLite blob ID
        chunk_size: Size of each chunk in bytes
    """
    if is_postgres() and oid:
        # PostgreSQL Large Object streaming
        # Open for reading (0x40000 = INV_READ)
        result = await db.execute(text("SELECT lo_open(:oid, 262144)"), {"oid": oid})
        fd = result.scalar()
        if fd is None:
            raise ValueError(f"Could not open Large Object {oid}")

        try:
            while True:
                result = await db.execute(
                    text("SELECT loread(:fd, :length)"), {"fd": fd, "length": chunk_size}
                )
                chunk = result.scalar()
                if not chunk:
                    break
                yield chunk
        finally:
            await db.execute(text("SELECT lo_close(:fd)"), {"fd": fd})

    elif blob_id:
        # SQLite BLOB streaming using SUBSTR
        # Get total size first
        total_size = await _get_blob_size(db, blob_id)

        for offset in range(0, total_size, chunk_size):
            length = min(chunk_size, total_size - offset)
            # Use raw SQL SUBSTR to avoid loading full blob into memory
            # SUBSTR in SQLite for blobs starts at 1, length follows
            result = await db.execute(
                text("SELECT SUBSTR(data, :start, :length) FROM audio_blobs WHERE id = :id"),
                {"start": offset + 1, "length": length, "id": blob_id},
            )
            chunk = result.scalar()
            if not chunk:
                break
            yield chunk
    else:
        raise ValueError("Either oid or blob_id must be provided")


async def delete_audio_data(
    db: AsyncSession, oid: int | None = None, blob_id: str | None = None
) -> bool:
    """Delete audio data from database"""
    if is_postgres() and oid:
        return await _delete_large_object(db, oid)
    elif blob_id:
        return await _delete_blob(db, blob_id)
    return False


async def get_audio_size(
    db: AsyncSession, oid: int | None = None, blob_id: str | None = None
) -> int:
    """Get audio data size in bytes"""
    if is_postgres() and oid:
        return await _get_lo_size(db, oid)
    elif blob_id:
        return await _get_blob_size(db, blob_id)
    return 0


# ========== PostgreSQL Large Object Implementation ==========


async def _save_large_object(db: AsyncSession, data: bytes) -> int:
    """Save data to PostgreSQL Large Object, return OID"""
    # Create large object
    result = await db.execute(text("SELECT lo_creat(-1)"))
    oid = result.scalar()

    # Open for writing (0x20000 = INV_WRITE)
    result = await db.execute(text("SELECT lo_open(:oid, 131072)"), {"oid": oid})
    fd = result.scalar()

    # Write data in chunks (16KB chunks)
    chunk_size = 16 * 1024
    for i in range(0, len(data), chunk_size):
        chunk = data[i : i + chunk_size]
        await db.execute(text("SELECT lowrite(:fd, :data)"), {"fd": fd, "data": chunk})

    # Close
    await db.execute(text("SELECT lo_close(:fd)"), {"fd": fd})

    logger.info(f"Saved Large Object OID: {oid}, size: {len(data)} bytes")
    return oid


async def _read_large_object(
    db: AsyncSession, oid: int, offset: int = 0, length: int = -1
) -> bytes:
    """Read from PostgreSQL Large Object with range support"""
    # Open for reading (0x40000 = INV_READ)
    result = await db.execute(text("SELECT lo_open(:oid, 262144)"), {"oid": oid})
    fd = result.scalar()

    if fd is None:
        raise ValueError(f"Could not open Large Object {oid}")

    # Seek if offset specified
    if offset > 0:
        await db.execute(text("SELECT lo_lseek(:fd, :offset, 0)"), {"fd": fd, "offset": offset})

    # Get total size if length not specified
    if length < 0:
        # Seek to end to get size
        result = await db.execute(text("SELECT lo_lseek(:fd, 0, 2)"), {"fd": fd})
        total_size = result.scalar()
        # Seek back to offset
        await db.execute(text("SELECT lo_lseek(:fd, :offset, 0)"), {"fd": fd, "offset": offset})
        length = total_size - offset

    # Read data
    result = await db.execute(text("SELECT loread(:fd, :length)"), {"fd": fd, "length": length})
    data = result.scalar()

    # Close
    await db.execute(text("SELECT lo_close(:fd)"), {"fd": fd})

    return data or b""


async def _delete_large_object(db: AsyncSession, oid: int) -> bool:
    """Delete PostgreSQL Large Object"""
    try:
        await db.execute(text("SELECT lo_unlink(:oid)"), {"oid": oid})
        logger.info(f"Deleted Large Object OID: {oid}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete Large Object {oid}: {e}")
        return False


async def _get_lo_size(db: AsyncSession, oid: int) -> int:
    """Get PostgreSQL Large Object size"""
    result = await db.execute(text("SELECT lo_open(:oid, 262144)"), {"oid": oid})
    fd = result.scalar()
    if fd is None:
        return 0

    # Seek to end
    result = await db.execute(text("SELECT lo_lseek(:fd, 0, 2)"), {"fd": fd})
    size = result.scalar() or 0

    await db.execute(text("SELECT lo_close(:fd)"), {"fd": fd})
    return size


# ========== SQLite BLOB Fallback Implementation ==========


async def _save_blob(db: AsyncSession, data: bytes) -> str:
    """Save data to SQLite AudioBlob table"""
    blob = AudioBlob(data=data)
    db.add(blob)
    await db.flush()
    logger.info(f"Saved Blob ID: {blob.id}, size: {len(data)} bytes")
    return blob.id


async def _read_blob(db: AsyncSession, blob_id: str, offset: int = 0, length: int = -1) -> bytes:
    """Read from SQLite AudioBlob with range support"""
    logger.info(
        f"[DEBUG] _read_blob called with blob_id={blob_id}, offset={offset}, length={length}"
    )

    result = await db.execute(select(AudioBlob).where(AudioBlob.id == blob_id))
    blob = result.scalar_one_or_none()

    if not blob:
        logger.error(f"[ERROR] Blob {blob_id} not found in AudioBlob table")
        raise ValueError(f"Blob {blob_id} not found")

    data = blob.data
    logger.info(f"[DEBUG] Read blob data with size={len(data) if data else 0} bytes")

    if offset > 0 or length >= 0:
        if length < 0:
            return data[offset:]
        return data[offset : offset + length]
    return data


async def _delete_blob(db: AsyncSession, blob_id: str) -> bool:
    """Delete SQLite AudioBlob"""
    try:
        result = await db.execute(select(AudioBlob).where(AudioBlob.id == blob_id))
        blob = result.scalar_one_or_none()
        if blob:
            await db.delete(blob)
            logger.info(f"Deleted Blob ID: {blob_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete Blob {blob_id}: {e}")
        return False


async def _get_blob_size(db: AsyncSession, blob_id: str) -> int:
    """Get SQLite AudioBlob size"""
    result = await db.execute(select(AudioBlob).where(AudioBlob.id == blob_id))
    blob = result.scalar_one_or_none()
    return len(blob.data) if blob else 0
