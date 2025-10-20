from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Query

from solaris_client import get_json
from auth import login as auth_login  # optional helper route uses this

app = FastAPI(title="Solaris Local Proxy", version="0.2.0")


# -------------------------
# Health / Auth utilities
# -------------------------

@app.get("/health")
def health() -> Dict[str, bool]:
    return {"ok": True}


@app.post("/auth/login")
def auth_login_route() -> Dict[str, Any]:
    """
    Force a fresh login using SOLARIS_USERNAME / SOLARIS_PASSWORD from .env.
    Returns ok + whether a token was obtained.
    """
    try:
        token = auth_login(force=True)
        return {"ok": True, "token_present": bool(token)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/auth/status")
def auth_status() -> Dict[str, Any]:
    """
    Quick ping to a protected endpoint to confirm auth is working.
    """
    try:
        profile = get_json("/user/profile")
        return {"ok": True, "profile": profile}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# -------------------------
# Data endpoints (proxy)
# -------------------------

@app.get("/wells/catalog")
def wells_catalog(
    limit: int = Query(40, ge=1, le=200),
    start: int = Query(0, ge=0),
) -> List[Dict[str, Any]]:
    """
    Proxies Solaris wells catalog.
    The upstream returns {"_meta": {...}, "info": {...}, "data": [ ... ]}.
    We return the list under "data" for convenience.
    """
    try:
        raw = get_json("/wells/catalog", params={"limit": limit, "start": start})
        return raw.get("data", [])
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/debug/fleets-event")
def debug_fleets_event(
    site_name: str = Query(..., description="e.g., WINANS 1216 NORTH"),
) -> Dict[str, Any]:
    """
    Return the raw fleets event payload to inspect exact field names.
    """
    try:
        return get_json("/fleets/event", params={"wellSiteName": site_name})
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/silo-levels")
def silo_levels(
    site_name: str = Query(..., description="e.g., WINANS 1216 NORTH"),
    fleet_ids: str | None = Query(
        None,
        description="Optional comma-separated fleet IDs if data is split across fleets (e.g., MSS157AB,MSS162AB).",
    ),
) -> Dict[str, Any]:
    """
    Normalized silo levels for a well site. If your site uses multiple fleets,
    pass them in fleet_ids and results will be merged.
    """
    try:
        def fetch(site: str, fleet: str | None = None) -> Dict[str, Any]:
            params: Dict[str, Any] = {"wellSiteName": site}
            if fleet:
                # Only include this if your tenant supports filtering by fleet; otherwise omit.
                params["fleetId"] = fleet
            return get_json("/fleets/event", params=params)

        raws: List[Dict[str, Any]] = []
        if fleet_ids:
            for fid in [x.strip() for x in fleet_ids.split(",") if x.strip()]:
                raws.append(fetch(site_name, fid))
        else:
            raws.append(fetch(site_name))

        silos: List[Dict[str, Any]] = []
        last_updates: List[Any] = []

        for raw in raws:
            # capture any plausible "last update" field for later max()
            last_updates.append(raw.get("lastUpdate") or raw.get("asOf") or raw.get("timestamp"))

            # find the list of silos in the payload
            source_list = raw.get("silos")
            if source_list is None:
                source_list = raw.get("data")
            if source_list is None:
                source_list = []

            for s in source_list:
                name = s.get("siloName") or s.get("name")
                percent = s.get("levelPercent") or s.get("percent")
                lbs = (
                    s.get("poundsAvailable")
                    or s.get("availableSandLbs")
                    or s.get("availableSand")
                )
                as_of = s.get("asOf") or s.get("timestamp")

                silos.append(
                    {
                        "name": name,
                        "percent": percent,
                        "lbs": lbs,
                        "as_of": as_of,
                    }
                )

        # choose the newest last_update if multiple fleets
        last_update = None
        for ts in last_updates:
            if ts is None:
                continue
            if last_update is None or str(ts) > str(last_update):
                last_update = ts

        return {
            "site": site_name,
            "last_update": last_update,
            "silos": silos,
        }

    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))