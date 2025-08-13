from __future__ import annotations

"""
Universal perf-table parser used by the Perf Converter tab.

Public API
----------
- extract_text_by_well(pdf_path, well_map) -> {well: raw_text}
- parse_pdf_structured(pdf_path, well_map, **knobs) -> {well: [(stage, plug, top, bottom), ...]}
- parse_pdf = alias of parse_pdf_structured (back-compat)

Design notes
------------
- Works for a variety of operator formats (explicit Top/Bottom per cluster, or flat cluster lists).
- Robust stage detection ("Stage 12", "12", and split digits like "1"|"2" -> 12).
- Table-first (lattice -> stream) with auto-rotation; text fallback.
- Numbers are reconstructed even when thousands separators get split across cells.
- Cluster selection is constrained to a window below the plug depth to avoid stray values.
- Stage 01 is **not** auto-null here (do it in the GUI); optionally set stage01_null=True to null it.

Dependencies: pdfplumber
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pdfplumber

# ----------------------------------------------------------------------------
# Data models
# ----------------------------------------------------------------------------

@dataclass
class PageRange:
    start: int  # 1-based inclusive
    end: int    # 1-based inclusive


@dataclass
class StageRow:
    stage: str
    plug: Optional[float]
    top: Optional[float]
    bottom: Optional[float]
    n_perf_vals: int = 0  # number of cluster values used to compute top/bottom


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------

def extract_text_by_well(pdf_path: str, well_map: Dict[str, Dict]) -> Dict[str, str]:
    """Return raw text for each well's page range (for debugging / OB payload)."""
    text_data: Dict[str, str] = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for well, info in well_map.items():
                pr = _page_range_from_info(info)
                if pr is None:
                    pr = _auto_find_well_pages(pdf, well) or PageRange(1, len(pdf.pages))
                chunks: List[str] = []
                for page_num in range(pr.start, pr.end + 1):
                    if 1 <= page_num <= len(pdf.pages):
                        page = pdf.pages[page_num - 1]
                        chunks.append(page.extract_text() or "")
                text_data[well] = "\n".join(chunks)
    except Exception as e:
        logging.exception("extract_text_by_well failed: %s", e)
        return {well: "" for well in well_map}
    return text_data


def parse_pdf(pdf_path: str, well_map: Dict[str, Dict], **kwargs):
    """Back-compat alias. Prefer parse_pdf_structured."""
    return parse_pdf_structured(pdf_path, well_map, **kwargs)


def parse_pdf_structured(
    pdf_path: str,
    well_map: Dict[str, Dict],
    *,
    min_depth: Optional[float] = None,          # None -> auto (use generic floor)
    window_below_plug: float = 1200.0,          # keep cluster MDs within this window below plug
    split_digit_stage: bool = True,             # handle stage digits split across cells
    prefer_explicit_top_bottom: bool = True,    # use header Top/Bottom columns if present
    stage01_null: bool = False,                 # force Stage 01 top/bottom = None (GUI can handle)
    page_search_window: int = 6                 # auto-find: pages after first well name hit
) -> Dict[str, List[Tuple[str, Optional[float], Optional[float], Optional[float]]]]:
    """
    Return structured perf data by well: {well: [("01", plug, top, bottom), ...]}.
    - Stages are zero-padded strings.
    - plug/top/bottom are floats (ftKB) or None.
    """
    out: Dict[str, List[Tuple[str, Optional[float], Optional[float], Optional[float]]]] = {}
    with pdfplumber.open(pdf_path) as pdf:
        for well, info in well_map.items():
            pr = _page_range_from_info(info)
            if pr is None:
                pr = _auto_find_well_pages(pdf, well, page_search_window) or PageRange(1, len(pdf.pages))

            # parse rows across pages
            rows_all: List[StageRow] = []
            for pnum in range(pr.start, pr.end + 1):
                if not (1 <= pnum <= len(pdf.pages)):
                    continue
                page = pdf.pages[pnum - 1]
                rows_all += _extract_structured_from_page(
                    page,
                    min_depth=min_depth,
                    window_below_plug=window_below_plug,
                    split_digit_stage=split_digit_stage,
                    prefer_explicit_top_bottom=prefer_explicit_top_bottom,
                )

            # de-dup: keep the row with the most perf values; if tie, prefer one with explicit top/bottom
            best_by_stage: Dict[str, StageRow] = {}
            for r in rows_all:
                s = r.stage
                if s not in best_by_stage:
                    best_by_stage[s] = r
                else:
                    cur = best_by_stage[s]
                    if r.n_perf_vals > cur.n_perf_vals:
                        best_by_stage[s] = r
                    elif r.n_perf_vals == cur.n_perf_vals:
                        # prefer row that has both top & bottom
                        cur_score = int(cur.top is not None) + int(cur.bottom is not None)
                        new_score = int(r.top is not None) + int(r.bottom is not None)
                        if new_score > cur_score:
                            best_by_stage[s] = r

            rows = [_normalize_row(v, stage01_null=stage01_null) for k, v in sorted(best_by_stage.items(), key=lambda kv: int(kv[0]))]
            out[well] = [(r.stage, r.plug, r.top, r.bottom) for r in rows]
    return out


# ----------------------------------------------------------------------------
# Internals
# ----------------------------------------------------------------------------

_DEF_MIN_DEPTH = 1000.0  # generic floor to ignore non-depth numbers


def _page_range_from_info(info: Dict) -> Optional[PageRange]:
    s, e = info.get("start_page"), info.get("end_page")
    if isinstance(s, int) and isinstance(e, int) and 1 <= s <= e:
        return PageRange(s, e)
    return None


def _auto_find_well_pages(pdf: pdfplumber.PDF, well_name: str, window: int = 6) -> Optional[PageRange]:
    pat = re.compile(re.escape(str(well_name)), re.IGNORECASE)
    for i, page in enumerate(pdf.pages, start=1):
        text = page.extract_text() or ""
        if pat.search(text):
            return PageRange(i, min(i + max(1, int(window)), len(pdf.pages)))
    return None


def _extract_structured_from_page(
    page: pdfplumber.page.Page,
    *,
    min_depth: Optional[float],
    window_below_plug: float,
    split_digit_stage: bool,
    prefer_explicit_top_bottom: bool,
) -> List[StageRow]:
    rows: List[StageRow] = []

    # try original + rotated variants
    candidates = [page]
    try:
        if page.width < page.height:
            candidates = [page.rotate(0), page.rotate(90)]
        else:
            candidates = [page.rotate(0), page.rotate(-90)]
    except Exception:
        pass

    for pg in candidates:
        tables = _extract_tables(pg)
        for t in tables:
            rows += _parse_table(t, min_depth=min_depth, window_below_plug=window_below_plug,
                                 split_digit_stage=split_digit_stage, prefer_explicit_top_bottom=prefer_explicit_top_bottom)

        if rows:
            break  # good enough from this orientation

    # Fallback: text lines
    if not rows:
        try:
            text = page.extract_text() or ""
            rows += _parse_text_lines(text, min_depth=min_depth, window_below_plug=window_below_plug)
        except Exception:
            pass

    return rows


def _extract_tables(page: pdfplumber.page.Page) -> List[List[List[str]]]:
    out = []
    lattice = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "join_tolerance": 3,
        "edge_min_length": 3,
        "min_words_vertical": 1,
        "min_words_horizontal": 1,
        "keep_blank_chars": False,
        "text_y_tolerance": 3,
        "text_x_tolerance": 2,
    }
    stream = {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "keep_blank_chars": False,
        "text_y_tolerance": 3,
        "text_x_tolerance": 2,
        "intersection_tolerance": 3,
        "snap_tolerance": 3,
        "min_words_vertical": 1,
        "min_words_horizontal": 1,
    }
    try:
        out += page.extract_tables(table_settings=lattice) or []
    except Exception:
        pass
    try:
        out += page.extract_tables(table_settings=stream) or []
    except Exception:
        pass
    return out


# ---------------------
# Table parsing helpers
# ---------------------

_STAGE_CELL_RE = re.compile(r"^(?:Stage\s*)?0*(\d{1,3})\b", re.IGNORECASE)
_NUM_CONTIG_RE = re.compile(r"-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d{4,}(?:\.\d+)?")
_CAN_BE_TOP = re.compile(r"top", re.IGNORECASE)
_CAN_BE_BOTTOM = re.compile(r"bot|bottom", re.IGNORECASE)
_CAN_BE_PLUG = re.compile(r"plug", re.IGNORECASE)


def _parse_table(
    table: List[List[str]],
    *,
    min_depth: Optional[float],
    window_below_plug: float,
    split_digit_stage: bool,
    prefer_explicit_top_bottom: bool,
) -> List[StageRow]:
    header_idx, header = _find_header(table)
    body = table[header_idx + 1 :] if header_idx is not None else table

    # Identify header-based columns
    top_cols: List[int] = []
    bottom_cols: List[int] = []
    plug_cols: List[int] = []

    if header is not None:
        for ci, h in enumerate(header):
            htxt = (h or "").strip()
            if _CAN_BE_TOP.search(htxt):
                top_cols.append(ci)
            if _CAN_BE_BOTTOM.search(htxt):
                bottom_cols.append(ci)
            if _CAN_BE_PLUG.search(htxt):
                plug_cols.append(ci)

    rows: List[StageRow] = []
    for raw in body:
        if not raw or not any(c for c in raw):
            continue

        stage_num = _detect_stage_from_row(raw, split_digit_stage=split_digit_stage)
        if stage_num is None:
            continue

        # Collect numbers
        numbers_all = _numbers_from_cells(raw)
        numbers = [n for n in numbers_all if n >= (min_depth or _DEF_MIN_DEPTH)]
        if not numbers:
            continue

        # Plug detection: prefer plug column(s) if present; else deepest number
        plug = None
        if plug_cols:
            plug_candidates: List[float] = []
            for ci in plug_cols:
                plug_candidates += _nums_from_cell(raw, ci)
            plug_candidates = [n for n in plug_candidates if n >= (min_depth or _DEF_MIN_DEPTH)]
            if plug_candidates:
                plug = max(plug_candidates)
        if plug is None:
            plug = max(numbers)

        # Cluster candidates near plug
        perf_candidates: List[float] = []
        if prefer_explicit_top_bottom and (top_cols or bottom_cols):
            if top_cols:
                for ci in top_cols:
                    perf_candidates += _nums_from_cell(raw, ci)
            if bottom_cols:
                for ci in bottom_cols:
                    perf_candidates += _nums_from_cell(raw, ci)
            perf_candidates = [n for n in perf_candidates if n < plug - 1e-3]
        else:
            perf_candidates = [n for n in numbers if n < plug - 1e-3]

        # Apply window below plug to avoid stray values (bounds, pay notes, etc.)
        perf_candidates = [n for n in perf_candidates if (plug - window_below_plug) <= n]

        top = min(perf_candidates) if perf_candidates else None
        bottom = max(perf_candidates) if perf_candidates else None

        rows.append(StageRow(stage=f"{stage_num:02d}", plug=plug, top=top, bottom=bottom, n_perf_vals=len(perf_candidates)))

    return rows


def _find_header(table: List[List[str]]) -> Tuple[Optional[int], Optional[List[str]]]:
    for i, row in enumerate(table[:6]):  # scan first few rows
        joined = " ".join([(c or "") for c in row]).lower()
        if any(k in joined for k in ("stage", "plug", "cluster", "top", "bottom")):
            return i, row
    return None, None


def _detect_stage_from_row(raw: List[str], *, split_digit_stage: bool) -> Optional[int]:
    # 1) direct match in first cells (handles "Stage 12", "12")
    for cell in raw[:6]:
        if not cell:
            continue
        s = str(cell).strip()
        m = _STAGE_CELL_RE.match(s)
        if m:
            return int(m.group(1))
    # 2) join first 2 cells that are single digits: "1" + "2" => 12
    if split_digit_stage:
        digs: List[str] = []
        for cell in raw[:2]:
            if not cell:
                continue
            s = str(cell).strip()
            if re.fullmatch(r"\d{1}", s):
                digs.append(s)
        if len(digs) == 2:
            try:
                return int("".join(digs))
            except Exception:
                pass
    return None


def _numbers_from_cells(row: List[str]) -> List[float]:
    out: List[float] = []
    cells = [(c or "").strip() for c in row]

    # 1) strict per-cell extraction
    for c in cells:
        out += _extract_numbers_loose(c)

    # 2) repair split-thousands across adjacent cells
    #   patterns we fix:
    #   - A) "16" | ",628"  -> 16,628
    #   - B) "16" | ",62" | "8" -> 16,628
    for i in range(len(cells) - 1):
        left = cells[i]
        right = cells[i + 1].replace(" ", "")
        if re.fullmatch(r"\d{1,3}", left) and re.fullmatch(r",\d{3}", right):
            token = left + right
            try:
                out.append(float(token.replace(",", "")))
            except Exception:
                pass

        if i + 2 < len(cells):
            mid = cells[i + 1].replace(" ", "")
            r2 = cells[i + 2].strip()
            if (
                re.fullmatch(r"\d{1,3}", left) and
                re.fullmatch(r",\d{2}", mid) and
                re.fullmatch(r"\d", r2)
            ):
                token = left + mid + r2  # e.g., "16" + ",62" + "8" -> "16,628"
                try:
                    out.append(float(token.replace(",", "")))
                except Exception:
                    pass

    return out



def _nums_from_cell(row: List[str], ci: int) -> List[float]:
    try:
        cell = row[ci]
    except Exception:
        return []
    return _extract_numbers_loose(str(cell or ""))


def _extract_numbers_loose(text: str) -> List[float]:
    nums: List[float] = []
    for m in _NUM_CONTIG_RE.findall(text or ""):
        try:
            nums.append(float(m.replace(",", "")))
        except Exception:
            pass
    return nums



def _parse_text_lines(text: str, *, min_depth: Optional[float], window_below_plug: float) -> List[StageRow]:
    rows: List[StageRow] = []
    for line in text.splitlines():
        m = _STAGE_CELL_RE.search(line)
        if not m:
            continue
        stage_num = int(m.group(1))
        nums = _extract_numbers_loose(line)
        nums = [n for n in nums if n >= (min_depth or _DEF_MIN_DEPTH)]
        if not nums:
            continue
        plug = max(nums)
        perf = [n for n in nums if (plug - window_below_plug) <= n < plug - 1e-3]
        top = min(perf) if perf else None
        bottom = max(perf) if perf else None
        rows.append(StageRow(stage=f"{stage_num:02d}", plug=plug, top=top, bottom=bottom, n_perf_vals=len(perf)))
    return rows


def _normalize_row(r: StageRow, *, stage01_null: bool) -> StageRow:
    stg = r.stage.zfill(2)
    top, bot = r.top, r.bottom
    if stage01_null and stg == "01":
        top, bot = None, None
    # ensure top <= bottom when both present
    if top is not None and bot is not None and top > bot:
        top, bot = bot, top
    return StageRow(stage=stg, plug=r.plug, top=top, bottom=bot, n_perf_vals=r.n_perf_vals)
