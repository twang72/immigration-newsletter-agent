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
