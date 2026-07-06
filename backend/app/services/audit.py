import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import AuditAction, AuditEvent


def record_audit_event(
    db: Session,
    *,
    store_id: int,
    action: AuditAction,
    entity_type: str,
    entity_id: int | str,
    actor_type: str = "system",
    actor_id: int | str | None = None,
    evidence: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        store_id=store_id,
        actor_type=actor_type,
        actor_id=str(actor_id) if actor_id is not None else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        evidence=json.dumps(evidence or {}, sort_keys=True),
    )
    db.add(event)
    return event


def list_audit_events(
    db: Session,
    *,
    store_id: int,
    limit: int = 100,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> list[AuditEvent]:
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.store_id == store_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    )
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)
    return list(db.scalars(stmt).all())
