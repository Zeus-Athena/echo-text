import asyncio
import sys

from sqlalchemy import select

from app.core.database import async_session
from app.models.recording import Recording, Transcript, Translation


async def debug_recording(title_query):
    async with async_session() as session:
        # 1. Find Recording (Latest 5)
        stmt = select(Recording).order_by(Recording.created_at.desc()).limit(5)
        result = await session.execute(stmt)
        recordings = result.scalars().all()

        if not recordings:
            print("No recordings found")
            return

        print(f"Found {len(recordings)} recent recordings:")
        for rec in recordings:
            print(f"- ID: {rec.id}, Title: {rec.title}, CreatedAt: {rec.created_at}")

        # If user provided a query, try to match it manually
        target_recording = None
        if title_query:
            for rec in recordings:
                if title_query in rec.title:
                    target_recording = rec
                    break

        if not target_recording:
            print(
                f"\nCould not match '{title_query}' in recent recordings. Using the most recent one: {recordings[0].title}"
            )
            target_recording = recordings[0]

        rec_id = target_recording.id
        print(f"\nAnalyzing Recording ID: {rec_id} (Title: {target_recording.title})")

        # 2. Get Transcript
        stmt = select(Transcript).where(Transcript.recording_id == rec_id)
        t_result = await session.execute(stmt)
        transcript = t_result.scalar_one_or_none()

        if transcript:
            print(f"\nTranscript Found (ID: {transcript.id}):")
            segments = transcript.segments or []
            print(f"Total Transcript Segments: {len(segments)}")
            for i, seg in enumerate(segments):
                # Only print first few and last few if too many
                if i < 5 or i > len(segments) - 5:
                    print(
                        f"  [{i}] Start: {seg.get('start')}, End: {seg.get('end')}, Final: {seg.get('is_final')}"
                    )
                    print(f"      Text: {seg.get('text')}")
        else:
            print("\nNo Transcript found.")

        # 3. Get Translation
        stmt = select(Translation).where(Translation.recording_id == rec_id)
        tr_result = await session.execute(stmt)
        translation = tr_result.scalar_one_or_none()

        if translation:
            print(f"\nTranslation Found (ID: {translation.id}):")
            print(f"Full Text Length: {len(translation.full_text or '')}")
            segments = translation.segments or []
            print(f"Total Translation Segments: {len(segments)}")
            for i, seg in enumerate(segments):
                print(f"  [{i}] SegID: {seg.get('segment_id')}")
                print(f"      Text: {seg.get('text')}")
        else:
            print("\nNo Translation found.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "录音 2025/12/30 16:20:21"

    asyncio.run(debug_recording(query))
