"""run_pipeline(): executes the 7 stages and keeps the latest StageReports in memory."""
import functools
import threading

from ..models import ensure_suspect_column
from . import stages as st

_lock = threading.Lock()
_run_lock = threading.RLock()
LATEST = {i: st.empty_report(i) for i in range(1, 8)}
LATEST_HUD: dict = {}


def reset_reports():
    with _lock:
        for i in range(1, 8):
            LATEST[i] = st.empty_report(i)
        LATEST_HUD.clear()


def status_reports():
    with _lock:
        return [dict(LATEST[i]) for i in range(1, 8)]


def run_pipeline(session, rows, default_source="USER-ENTERED"):
    """Run all stages over raw row dicts; commits on success. Returns IngestResult."""
    from ..api.settings import effective  # persisted thresholds/weights (M7)
    cfg, weights, _ = effective(session)
    ensure_suspect_column(session)
    ctx = st.Ctx(session=session, raw=list(rows), default_source=default_source)
    reports = []
    with _run_lock:
        orig = st.assess
        st.assess = functools.partial(orig, cfg=cfg, weights=weights)
        try:
            for fn in (st.stage1_ingest, st.stage2_validate, st.stage3_baseline, st.stage4_triage,
                       st.stage5_grade, st.stage6_hud, st.stage7_alerts):
                reports.append(fn(ctx))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            st.assess = orig
    with _lock:
        for r in reports:
            LATEST[r["stage"]] = r
        LATEST_HUD.update(ctx.hud)
    return {"received": len(ctx.raw), "accepted": len(ctx.items), "rejected": ctx.rejected,
            "suspect": ctx.suspect, "assessments": ctx.assessments, "pipeline": reports}

