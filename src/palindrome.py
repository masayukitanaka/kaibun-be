import json
import os
import re
import sqlite3
from collections import deque
from pathlib import Path

from flask import Blueprint, jsonify, request

from .palindrome_engine import (
    generate_initial_states, extend_left, extend_right,
)

palindrome_bp = Blueprint("palindrome", __name__)

DB_PATH = Path(__file__).resolve().parent.parent / "bunsetsu.db"

MAX_SEEDS = 200
CANDIDATE_LIMIT = 1000
MIN_BUNSETSU = 2
MAX_BUNSETSU = 4
MAX_RESULTS = 100
DEFICIT_THRESHOLD = 2

_JP_RE = re.compile(r'^[ぁ-んァ-ヶー\u4E00-\u9FFF々〇]+$')
_HIRAGANA_RE = re.compile(r'^[ぁ-んー]+$')
EXCLUDE_WORDS = ["悔過"]


def _get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _prefix_range(prefix):
    upper = prefix[:-1] + chr(ord(prefix[-1]) + 1)
    return prefix, upper


def _query_by_prefix(cur, column, prefix, limit=CANDIDATE_LIMIT):
    lo, hi = _prefix_range(prefix)
    return cur.execute(
        f"SELECT kana, display FROM bunsetsu WHERE {column} >= ? AND {column} < ? LIMIT ?",
        (lo, hi, limit),
    ).fetchall()


def _has_search_tables(cur):
    row = cur.execute(
        "SELECT COUNT(*) FROM sqlite_master "
        "WHERE type='table' AND name IN ('extend_candidates','reachable')"
    ).fetchone()
    return row[0] == 2


def _find_seeds(cur, keyword):
    if _HIRAGANA_RE.match(keyword):
        return _query_by_prefix(cur, "kana", keyword, limit=MAX_SEEDS)
    else:
        return _query_by_prefix(cur, "display", keyword, limit=MAX_SEEDS)


def _get_candidates(cur, state, use_tables=False, remaining_steps=99):
    candidates = []

    if state.L:
        L = state.L
        ll = len(L)
        for length in range(1, ll + 1):
            suffix = L[ll - length:]
            rows = cur.execute(
                "SELECT kana, display FROM bunsetsu WHERE kana = ?", (suffix,)
            ).fetchall()
            candidates.extend(rows)
        if use_tables and ll <= DEFICIT_THRESHOLD:
            rows = cur.execute(
                "SELECT DISTINCT w_kana, w_display "
                "FROM extend_candidates "
                "WHERE deficit = ? AND side = 'L' AND reach_steps <= ? "
                "ORDER BY reach_steps LIMIT ?",
                (L, remaining_steps - 1, CANDIDATE_LIMIT),
            ).fetchall()
            candidates.extend(rows)
        else:
            rev_L = L[::-1]
            candidates.extend(_query_by_prefix(cur, "kana_rev", rev_L))

    if state.R:
        R = state.R
        rl = len(R)
        for length in range(1, rl + 1):
            prefix = R[:length]
            rows = cur.execute(
                "SELECT kana, display FROM bunsetsu WHERE kana = ?", (prefix,)
            ).fetchall()
            candidates.extend(rows)
        if use_tables and rl <= DEFICIT_THRESHOLD:
            rows = cur.execute(
                "SELECT DISTINCT w_kana, w_display "
                "FROM extend_candidates "
                "WHERE deficit = ? AND side = 'R' AND reach_steps <= ? "
                "ORDER BY reach_steps LIMIT ?",
                (R, remaining_steps - 1, CANDIDATE_LIMIT),
            ).fetchall()
            candidates.extend(rows)
        else:
            candidates.extend(_query_by_prefix(cur, "kana", R))

    return candidates


def _search_at_depth(cur, seed_kana, seed_display, target_depth, use_tables=False):
    results = []
    queue = deque(generate_initial_states(seed_kana, seed_display))
    visited = set()

    while queue:
        state = queue.popleft()
        key = (state.L, state.H, state.R)
        if key in visited:
            continue
        visited.add(key)

        if state.is_palindrome_state():
            if state.bunsetsu_count >= MIN_BUNSETSU:
                results.append(state)
            continue

        if state.bunsetsu_count >= target_depth:
            continue

        remaining = target_depth - state.bunsetsu_count
        cands = _get_candidates(cur, state, use_tables=use_tables,
                                remaining_steps=remaining)

        for w_kana, w_display in cands:
            if state.L:
                ns = extend_left(state, w_kana, w_display)
                if ns and (ns.L, ns.H, ns.R) not in visited:
                    queue.append(ns)
            if state.R:
                ns = extend_right(state, w_kana, w_display)
                if ns and (ns.L, ns.H, ns.R) not in visited:
                    queue.append(ns)

    return results


@palindrome_bp.route("/palindrome")
def palindrome():
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return jsonify(error="keyword パラメータが必要です"), 400

    conn = _get_db()
    cur = conn.cursor()
    use_tables = _has_search_tables(cur)

    try:
        seeds = _find_seeds(cur, keyword)
        if not seeds:
            return jsonify(keyword=keyword, count=0, results=[])

        all_results = []
        seen_h = set()
        exact_seeds = [(k, d) for k, d in seeds if k == keyword or d == keyword]
        if not exact_seeds:
            exact_seeds = seeds[:1]

        for depth in range(MIN_BUNSETSU, MAX_BUNSETSU + 1):
            depth_seeds = seeds if depth <= 3 else exact_seeds
            for seed_kana, seed_display in depth_seeds:
                for state in _search_at_depth(cur, seed_kana, seed_display,
                                              target_depth=depth,
                                              use_tables=use_tables):
                    if (state.H not in seen_h
                            and _JP_RE.match(state.display)
                            and not any(w in state.display for w in EXCLUDE_WORDS)):
                        seen_h.add(state.H)
                        all_results.append(state)

        all_results.sort(key=lambda s: -len(s.H))

        file_dir = os.environ.get("FILE_DIR", "/tmp")
        out_dir = Path(file_dir) / "kaibun"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{keyword}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for s in all_results:
                f.write(json.dumps(
                    {"display": s.display, "kana": s.H, "bunsetsu_count": s.bunsetsu_count},
                    ensure_ascii=False,
                ) + "\n")

        shown = all_results[:MAX_RESULTS]

        return jsonify(
            keyword=keyword,
            count=len(all_results),
            results=[
                {
                    "display": s.display,
                    "kana": s.H,
                    "bunsetsu_count": s.bunsetsu_count,
                }
                for s in shown
            ],
        )
    finally:
        conn.close()
