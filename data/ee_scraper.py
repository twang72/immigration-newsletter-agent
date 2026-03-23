"""
Scrapes Express Entry draw history from IRCC and stores it in SQLite.
Source: https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/rounds-invitations.html

Each run fetches the latest draws and upserts them — safe to run repeatedly.
"""

import re
import httpx
from bs4 import BeautifulSoup
from data.db import init_db, upsert_ee_draw, get_recent_ee_draws

EE_DRAWS_URL = (
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/"
    "immigrate-canada/express-entry/rounds-invitations.html"
)


def parse_score(text: str) -> int:
    """Extract integer CRS score from messy text."""
    match = re.search(r"[\d,]+", text.replace(",", ""))
    return int(match.group()) if match else 0


def parse_invitations(text: str) -> int:
    match = re.search(r"[\d,]+", text.replace(",", ""))
    return int(match.group()) if match else 0


def normalize_draw_type(raw: str) -> str:
    """Normalize draw type labels to consistent categories."""
    raw = raw.strip()
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
    if "no program" in lower or "comprehensive" in lower or "crs" in lower:
        return "General CRS"
    return raw  # keep original if unrecognized


def scrape_ee_draws() -> list[dict]:
    print("[ee_scraper] Fetching Express Entry draw history from IRCC...")
    resp = httpx.get(EE_DRAWS_URL, timeout=30, follow_redirects=True)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    draws = []

    # IRCC renders draws in a <table> or in individual <details> accordion blocks
    # Try table first
    table = soup.find("table")
    if table:
        rows = table.find_all("tr")[1:]  # skip header
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if len(cols) < 4:
                continue
            try:
                draw = {
                    "draw_number": int(re.search(r"\d+", cols[0]).group()),
                    "draw_date": cols[1],
                    "draw_type": normalize_draw_type(cols[2]),
                    "cutoff_score": parse_score(cols[3]),
                    "invitations": parse_invitations(cols[4]) if len(cols) > 4 else 0,
                    "tie_break_date": cols[5] if len(cols) > 5 else None,
                }
                draws.append(draw)
            except Exception as e:
                print(f"[ee_scraper] Skipping row {cols}: {e}")
        return draws

    # Fallback: parse <details> accordion blocks (newer IRCC format)
    blocks = soup.find_all("details")
    for block in blocks:
        summary = block.find("summary")
        if not summary:
            continue
        summary_text = summary.get_text(strip=True)
        # Look for draw number and date in summary
        draw_num_match = re.search(r"Draw\s*#?\s*(\d+)", summary_text, re.IGNORECASE)
        if not draw_num_match:
            continue

        text = block.get_text(" ", strip=True)
        date_match = re.search(r"(\w+ \d{1,2},? \d{4})", text)
        type_match = re.search(r"Type of round[:\s]+([^\n]+)", text, re.IGNORECASE)
        score_match = re.search(r"CRS score[:\s]+(\d+)", text, re.IGNORECASE)
        inv_match = re.search(r"Invitations[:\s]+([\d,]+)", text, re.IGNORECASE)

        try:
            draw = {
                "draw_number": int(draw_num_match.group(1)),
                "draw_date": date_match.group(1) if date_match else "",
                "draw_type": normalize_draw_type(type_match.group(1) if type_match else "General CRS"),
                "cutoff_score": int(score_match.group(1)) if score_match else 0,
                "invitations": parse_invitations(inv_match.group(1)) if inv_match else 0,
                "tie_break_date": None,
            }
            draws.append(draw)
        except Exception as e:
            print(f"[ee_scraper] Skipping block: {e}")

    return draws


def run_scraper() -> int:
    """Scrape and store all draws. Returns count of draws stored."""
    init_db()
    draws = scrape_ee_draws()
    if not draws:
        print("[ee_scraper] No draws found — IRCC page structure may have changed.")
        return 0

    for draw in draws:
        upsert_ee_draw(draw)

    print(f"[ee_scraper] Stored {len(draws)} draws.")
    return len(draws)


if __name__ == "__main__":
    count = run_scraper()
    recent = get_recent_ee_draws(5)
    print("\nMost recent draws:")
    for d in recent:
        print(f"  Draw #{d['draw_number']} | {d['draw_date']} | {d['draw_type']} | CRS: {d['cutoff_score']} | Invites: {d['invitations']}")
