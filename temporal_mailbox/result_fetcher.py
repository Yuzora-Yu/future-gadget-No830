from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date

from .config import MIZUHO_LOTO7_URL
from .models import Loto7Result


class ResultNotPublished(RuntimeError):
    pass


class ResultPageChanged(RuntimeError):
    pass


DRAW_RE = re.compile(r"第\s*(\d{1,4})\s*回")
DATE_RE = re.compile(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
NUMBER_RE = re.compile(r"(?<!\d)(?:0?[1-9]|[12]\d|3[0-7])(?!\d)")


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"[\t\r ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _numbers_between(
    block: str,
    start_label: str,
    end_labels: tuple[str, ...],
    count: int,
) -> tuple[int, ...] | None:
    start = block.find(start_label)
    if start < 0:
        return None
    tail = block[start + len(start_label) :]
    ends = [tail.find(label) for label in end_labels if tail.find(label) >= 0]
    segment = tail[: min(ends)] if ends else tail
    values = tuple(int(value) for value in NUMBER_RE.findall(segment))
    return values[:count] if len(values) >= count else None


def _candidate_blocks(text: str) -> list[tuple[int, str]]:
    matches = list(DRAW_RE.finditer(text))
    blocks: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append((int(match.group(1)), text[match.start() : end]))
    return blocks


def parse_mizuho_text(text: str, expected_date: date) -> Loto7Result:
    normalized = normalize_text(text)
    expected_date_text = f"{expected_date.year}年{expected_date.month}月{expected_date.day}日"

    for draw, block in _candidate_blocks(normalized):
        date_match = DATE_RE.search(block)
        if not date_match:
            continue
        found_date = date(*(int(part) for part in date_match.groups()))
        if found_date != expected_date:
            continue
        main = _numbers_between(block, "本数字", ("ボーナス数字",), 7)
        bonus = _numbers_between(
            block,
            "ボーナス数字",
            ("等級", "販売実績額", "キャリーオーバー", "当せん条件"),
            2,
        )
        if main and bonus:
            result = Loto7Result(
                draw=draw,
                draw_date=found_date,
                main=tuple(sorted(main)),
                bonus=tuple(sorted(bonus)),
                source_url=MIZUHO_LOTO7_URL,
                source_sha256=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            )
            result.validate()
            return result

    compact = re.sub(r"\s+", " ", normalized)
    anchor = compact.find(expected_date_text)
    if anchor >= 0:
        left = compact[max(0, anchor - 200) : anchor]
        right = compact[anchor : anchor + 1200]
        draw_matches = list(DRAW_RE.finditer(left))
        draw = int(draw_matches[-1].group(1)) if draw_matches else None
        main = _numbers_between(right, "本数字", ("ボーナス数字",), 7)
        bonus = _numbers_between(
            right,
            "ボーナス数字",
            ("等級", "販売実績額", "キャリーオーバー", "当せん条件"),
            2,
        )
        if draw and main and bonus:
            result = Loto7Result(
                draw=draw,
                draw_date=expected_date,
                main=tuple(sorted(main)),
                bonus=tuple(sorted(bonus)),
                source_url=MIZUHO_LOTO7_URL,
                source_sha256=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            )
            result.validate()
            return result

    if expected_date_text not in compact:
        raise ResultNotPublished(
            f"Mizuho has not published the {expected_date.isoformat()} draw yet"
        )
    raise ResultPageChanged(
        "the expected date is present, but the official result table could not be parsed"
    )


def fetch_official_result(expected_date: date) -> Loto7Result:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Playwright is required for transmission. Install the transmit extra."
        ) from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            ),
            extra_http_headers={"Accept-Language": "ja,en-US;q=0.8,en;q=0.6"},
        )
        page = context.new_page()
        try:
            page.goto(MIZUHO_LOTO7_URL, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(8_000)
            text = page.locator("body").inner_text(timeout=20_000)
            return parse_mizuho_text(text, expected_date)
        finally:
            context.close()
            browser.close()
