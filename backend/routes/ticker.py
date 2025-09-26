# backend/routes/ticker.py
from flask import Blueprint, request, jsonify
from flask_login import login_required
import json

bp = Blueprint("ticker", __name__, url_prefix="/api/ticker")

def q1(sql, params=()):
    return current_app.db.fetch_one(sql, params)  # adapt to your db wrapper
def qn(sql, params=()):
    return current_app.db.fetch_all(sql, params)
def execsql(sql, params=()):
    return current_app.db.execute(sql, params)

@bp.get("/<league_id>")
def get_public(league_id):
    settings = q1("SELECT enabled, theme FROM ticker_settings WHERE league_id=%s", (league_id,))
    if not settings or not settings["enabled"]:
        return jsonify({"enabled": False, "items": []})
    items = qn("""
        SELECT id, status, start_time, home_name, away_name, home_score, away_score,
               home_logo, away_logo, venue, link_url
        FROM ticker_items
        WHERE league_id=%s
        ORDER BY sort_key DESC, id DESC
        LIMIT 100
    """, (league_id,))
    return jsonify({"enabled": True, "theme": settings["theme"], "items": items})

@bp.put("/admin/<league_id>/settings")
@login_required
def put_settings(league_id):
    body = request.get_json(silent=True) or {}
    enabled = bool(body.get("enabled", False))
    theme = body.get("theme", {})
    source = body.get("source")
    execsql("""
        INSERT INTO ticker_settings (league_id, enabled, theme, source)
        VALUES (%s, %s, %s::jsonb, COALESCE(%s::jsonb, '{"mode":"manual","externalUrl":null,"competitionIds":[]}'))
        ON CONFLICT (league_id) DO UPDATE
        SET enabled=EXCLUDED.enabled,
            theme=EXCLUDED.theme,
            source=COALESCE(EXCLUDED.source, ticker_settings.source),
            updated_at=NOW()
    """, (league_id, enabled, json.dumps(theme), json.dumps(source) if source is not None else None))
    return jsonify({"ok": True})

@bp.post("/admin/<league_id>/items")
@login_required
def post_item(league_id):
    b = request.get_json(silent=True) or {}
    execsql("""INSERT INTO ticker_items
      (league_id, start_time, status, home_name, away_name, home_score, away_score,
       home_logo, away_logo, venue, link_url, sort_key)
      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,COALESCE(%s,NOW()))""",
      (league_id, b.get("start_time"), b.get("status",'SCHEDULED'),
       b["home_name"], b["away_name"], b.get("home_score"), b.get("away_score"),
       b.get("home_logo"), b.get("away_logo"), b.get("venue"), b.get("link_url"), b.get("sort_key")))
    return jsonify({"ok": True})

@bp.delete("/admin/<league_id>/items/<int:item_id>")
@login_required
def delete_item(league_id, item_id):
    execsql("DELETE FROM ticker_items WHERE id=%s AND league_id=%s", (item_id, league_id))
    return jsonify({"ok": True})
