"""
Fetches Express Entry draw history from IRCC's JSON endpoint and stores it in SQLite.
IRCC serves draw data as a JSON file — much more reliable than HTML scraping.
Source: https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json
"""

import httpx
from data.db import init_db, upsert_ee_draw, get_recent_ee_draws

EE_JSON_URL = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json"


def normalize_draw_type(raw: str) -> str:
    if not raw:
        return "General CRS"
    lower = raw.lower()
    if "healthcare" in lower or "health" in lower:
        return "Healthcare"
    if "stem" in lower:
        return "STEM"
    if "trade" in lower:
        return "Trades"
    if "french" in lower:
        return "French Language"
    if "agriculture" in lower or "agri" in lower:
        return "Agriculture"
    if "transport" in lower:
        return "Transport"
    if "education" in lower:
        return "Education"
    if "pnp" in lower or "provincial" in lower:
        return "PNP"
    if "no program" in lower or "comprehensive" in lower or "general" in lower:
        return "General CRS"
    return raw.strip()


def scrape_ee_draws() -> list[dict]:
    print("[ee_scraper] Fetching Express Entry draws from IRCC JSON endpoint...")
    resp = httpx.get(EE_JSON_URL, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    data = resp.json()

    # IRCC JSON structure: { "rounds": [ { "drawNumber": "...", "drawDate": "...", ... } ] }
    rounds = data.get("rounds", [])
    draws = []

    for r in rounds:
        try:
            draw_number = int(r.get("drawNumber", 0))
            if draw_number == 0:
                continue

            # Draw type: IRCC uses "drawName" for category draws
            draw_name = r.get("drawName", "") or r.get("drawNameEN", "") or ""
            draw_type = normalize_draw_type(draw_name if draw_name else "General CRS")

            # CRS score
            cutoff_raw = r.get("drawCRS", "") or r.get("dd1", "") or "0"
            try:
                cutoff_score = int(str(cutoff_raw).replace(",", "").strip())
            except ValueError:
                cutoff_score = 0

            # Invitations issued
            inv_raw = r.get("drawSize", "") or r.get("dd2", "") or "0"
            try:
                invitations = int(str(inv_raw).replace(",", "").strip())
            except ValueError:
                invitations = 0

            draw = {
                "draw_number": draw_number,
                "draw_date": r.get("drawDate", ""),
                "draw_type": draw_type,
                "cutoff_score": cutoff_score,
                "invitations": invitations,
                "tie_break_date": r.get("drawDateFull", None),
                # Score band distribution — how many candidates in each CRS range
                "dd1": r.get("dd1", 0),   # 601-1200
                "dd2": r.get("dd2", 0),   # 501-600
                "dd3": r.get("dd3", 0),   # 491-500
                "dd4": r.get("dd4", 0),   # 481-490
                "dd5": r.get("dd5", 0),   # 471-480
                "dd6": r.get("dd6", 0),   # 461-470
                "dd7": r.get("dd7", 0),   # 451-460
                "dd8": r.get("dd8", 0),   # 441-450
                "dd9": r.get("dd9", 0),   # 431-440
                "dd10": r.get("dd10", 0), # 421-430
                "dd11": r.get("dd11", 0), # 411-420
                "dd12": r.get("dd12", 0), # 401-410
                "dd13": r.get("dd13", 0), # 391-400
                "dd14": r.get("dd14", 0), # 381-390
                "dd15": r.get("dd15", 0), # 371-380
                "dd16": r.get("dd16", 0), # 361-370
                "dd17": r.get("dd17", 0), # 351-360
                "dd18": r.get("dd18", 0), # 301-350
            }
            draws.append(draw)
        except Exception as e:
            print(f"[ee_scraper] Skipping draw entry: {e} — {r}")

    print(f"[ee_scraper] Parsed {len(draws)} draws from IRCC.")
    return draws


def run_scraper() -> int:
    init_db()
    draws = scrape_ee_draws()
    if not draws:
        print("[ee_scraper] No draws found.")
        return 0
    for draw in draws:
        upsert_ee_draw(draw)
    print(f"[ee_scraper] Stored {len(draws)} draws in database.")
    return len(draws)


if __name__ == "__main__":
    count = run_scraper()
    recent = get_recent_ee_draws(5)
    print("\nMost recent draws:")
    for d in recent:
        print(f"  Draw #{d['draw_number']} | {d['draw_date']} | {d['draw_type']} | CRS: {d['cutoff_score']} | Invites: {d['invitations']}")
