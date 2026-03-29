"""
/api/v1/import — Watch history ingestion endpoints.

Supports:
  - Netflix: CSV export from /viewingactivity
  - Amazon Prime / Hotstar: CSV from community exporter scripts
  - MyAnimeList: XML export from panel.php?go=export

All imports are idempotent — re-uploading the same file won't create duplicates
(we upsert on a composite key: uid + platform + title).
"""

import csv
import io
import xml.etree.ElementTree as ET
from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from app.models.schemas import ImportResult, Platform, WatchEvent
from app.services.firebase import get_db
from app.dependencies import get_current_user
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB guard


# ── Netflix CSV Parser ─────────────────────────────────────────────────────────

def _parse_netflix_csv(content: str) -> list[WatchEvent]:
    """
    Parse Netflix viewing activity CSV.
    Expected columns: Title, Date
    """
    events = []
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        title = row.get("Title", "").strip()
        date  = row.get("Date", "").strip()
        if not title:
            continue
        events.append(WatchEvent(
            title=title,
            platform=Platform.NETFLIX,
            watched_at=date or None,
        ))
    return events


# ── Prime Video / Hotstar CSV Parser ──────────────────────────────────────────

def _parse_prime_csv(content: str) -> list[WatchEvent]:
    """
    Parse the community exporter CSV.
    Expected columns: date_watched, title, episode (optional)
    Column names vary by exporter version — we try a few.
    """
    events = []
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        # Normalize column names to lowercase
        row_lower = {k.lower().strip(): v for k, v in row.items()}
        title = (
            row_lower.get("title")
            or row_lower.get("name")
            or row_lower.get("show title", "")
        ).strip()
        date = row_lower.get("date_watched") or row_lower.get("date") or ""
        episode = row_lower.get("episode", "").strip() or None

        if not title:
            continue
        events.append(WatchEvent(
            title=title,
            platform=Platform.PRIME,  # caller overrides for Hotstar if needed
            watched_at=date.strip() or None,
            episode=episode,
        ))
    return events


# ── MyAnimeList XML Parser ─────────────────────────────────────────────────────

def _parse_mal_xml(content: str) -> list[WatchEvent]:
    """
    Parse MAL export XML.
    Structure:
      <myanimelist>
        <anime>
          <series_title>...</series_title>
          <my_status>Completed</my_status>
          <my_finish_date>...</my_finish_date>
        </anime>
      </myanimelist>
    """
    events = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML: {exc}")

    for anime in root.findall("anime"):
        title  = (anime.findtext("series_title") or "").strip()
        status = (anime.findtext("my_status") or "").strip()
        date   = (anime.findtext("my_finish_date") or "").strip()

        if not title:
            continue
        # Only import titles the user has actually seen
        if status.lower() not in ("completed", "watching", "on-hold"):
            continue

        events.append(WatchEvent(
            title=title,
            platform=Platform.MAL,
            watched_at=date if date and date != "0000-00-00" else None,
        ))
    return events


# ── Persistence helper ─────────────────────────────────────────────────────────

def _persist_events(uid: str, events: list[WatchEvent], db) -> tuple[int, int]:
    """
    Upsert watch events into Firestore.
    Returns (new_count, skipped_count).
    """
    new_count = 0
    skipped   = 0

    for event in events:
        # Composite key prevents duplicates
        doc_id = f"{uid}_{event.platform.value}_{event.title[:80].replace('/', '_')}"
        doc_ref = db.collection("watch_history").document(doc_id)

        if doc_ref.get().exists:
            skipped += 1
            continue

        doc_ref.set({
            "uid":        uid,
            "title":      event.title,
            "platform":   event.platform.value,
            "watched_at": event.watched_at,
            "episode":    event.episode,
            "genres":     [],   # populated asynchronously by enrichment job
            "title_id":   None, # populated after TMDB/MAL title matching
            "imported_at": datetime.utcnow().isoformat(),
        })
        new_count += 1

    return new_count, skipped


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/netflix", response_model=ImportResult, summary="Import Netflix viewing history CSV")
async def import_netflix(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    raw = await file.read()
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large (max 10 MB).")

    try:
        events = _parse_netflix_csv(raw.decode("utf-8", errors="replace"))
    except Exception as exc:
        raise HTTPException(400, f"Failed to parse Netflix CSV: {exc}")

    db = get_db()
    new_count, skipped = _persist_events(user["uid"], events, db)

    return ImportResult(
        platform=Platform.NETFLIX,
        parsed_count=len(events),
        new_titles=new_count,
        skipped=skipped,
    )


@router.post("/prime", response_model=ImportResult, summary="Import Prime Video / Hotstar history CSV")
async def import_prime(
    file: UploadFile = File(...),
    platform: str = "prime",  # Query param: "prime" | "hotstar"
    user: dict = Depends(get_current_user),
):
    raw = await file.read()
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large (max 10 MB).")

    plat = Platform.HOTSTAR if platform == "hotstar" else Platform.PRIME

    try:
        events = _parse_prime_csv(raw.decode("utf-8", errors="replace"))
        for e in events:
            e.platform = plat
    except Exception as exc:
        raise HTTPException(400, f"Failed to parse CSV: {exc}")

    db = get_db()
    new_count, skipped = _persist_events(user["uid"], events, db)

    return ImportResult(
        platform=plat,
        parsed_count=len(events),
        new_titles=new_count,
        skipped=skipped,
    )


@router.post("/mal", response_model=ImportResult, summary="Import MyAnimeList XML export")
async def import_mal(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    raw = await file.read()
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large (max 10 MB).")

    try:
        events = _parse_mal_xml(raw.decode("utf-8", errors="replace"))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(400, f"Failed to parse MAL XML: {exc}")

    db = get_db()
    new_count, skipped = _persist_events(user["uid"], events, db)

    return ImportResult(
        platform=Platform.MAL,
        parsed_count=len(events),
        new_titles=new_count,
        skipped=skipped,
    )


@router.get("/status", summary="Get import summary for the current user")
async def import_status(user: dict = Depends(get_current_user)):
    """Return counts of imported titles grouped by platform."""
    db = get_db()
    docs = (
        db.collection("watch_history")
        .where("uid", "==", user["uid"])
        .stream()
    )
    counts: dict[str, int] = {}
    for d in docs:
        plat = d.to_dict().get("platform", "unknown")
        counts[plat] = counts.get(plat, 0) + 1

    return {"totals": counts, "grand_total": sum(counts.values())}
