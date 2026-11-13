from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.orm import FeatureEvent
from backend.schemas.event import EventRecord, ExperimentResults, VariationResult


async def insert_events(db: AsyncSession, project_id: str, events: list[EventRecord]) -> None:
    if not events:
        return
    now = datetime.now(timezone.utc)
    rows = [
        FeatureEvent(
            project_id=project_id,
            flag_key=e.flag_key,
            event_type=e.event_type,
            variation_index=e.variation_index,
            user_id=e.user_id,
            attributes=e.attributes,
            received_at=e.timestamp or now,
        )
        for e in events
    ]
    db.add_all(rows)
    await db.commit()


async def get_experiment_results(
    db: AsyncSession, project_id: str, flag_key: str
) -> ExperimentResults:
    result = await db.execute(
        text("""
            SELECT
                variation_index,
                COUNT(*) FILTER (WHERE event_type = 'exposure')  AS exposures,
                COUNT(*) FILTER (WHERE event_type = 'conversion') AS conversions
            FROM events
            WHERE project_id = :project AND flag_key = :key
            GROUP BY variation_index
            ORDER BY variation_index
        """),
        {"project": project_id, "key": flag_key},
    )
    rows = result.fetchall()
    variations = []
    for row in rows:
        exposures = row.exposures
        conversions = row.conversions
        rate = round(100.0 * conversions / exposures, 2) if exposures > 0 else None
        variations.append(VariationResult(
            variation_index=row.variation_index,
            exposures=exposures,
            conversions=conversions,
            conversion_rate_pct=rate,
        ))
    return ExperimentResults(flag_key=flag_key, variations=variations)
