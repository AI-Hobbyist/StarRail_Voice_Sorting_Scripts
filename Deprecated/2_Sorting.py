"""Sort decoded Star Rail voice WAVs using legacy or current index workbooks."""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

LANGUAGE_FOLDERS = {"CHS": "中文 - Chinese", "EN": "英语 - English", "JP": "日语 - Japanese", "KR": "韩语 - Korean"}
BATTLE_FOLDER = "战斗语音 - Battle"
INVALID_PATH = re.compile(r'[<>:"/\\|?*]')
HTML_TAG = re.compile(r"<.*?>")


def as_text(value: Any) -> str:
    return "" if pd.isna(value) else str(value)


def safe_name(value: str, fallback: str) -> str:
    value = INVALID_PATH.sub("_", value).strip().rstrip(".")
    return value or fallback


def clean_text(value: str) -> str:
    return html.unescape(HTML_TAG.sub("", value)).replace("\n", " ").strip()


def read_rows(index_path: Path) -> list[dict[str, str]]:
    frame = pd.read_excel(index_path, dtype=object).fillna("")
    battle_column = "是否为战斗语音" if "是否为战斗语音" in frame.columns else None
    source_column = "数据来源" if "数据来源" in frame.columns else None
    rows = []
    for _, raw in frame.iterrows():
        # Column positions keep old four-column workbooks compatible.
        get = lambda index: as_text(raw.iloc[index]) if index < len(raw) else ""
        rows.append({
            "hash": get(0), "file": get(1), "character": get(2), "text": get(3),
            "source": as_text(raw[source_column]) if source_column else "",
            "battle": bool(battle_column and as_text(raw[battle_column]).lower() == "true"),
        })
    return rows


def load_battle_map(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def make_plan(
    rows: list[dict[str, str]], source: Path, output: Path, language: str, battle_map: dict[str, dict[str, Any]], battle_source: Path | None,
) -> tuple[list[tuple[Path, Path, str]], Counter[str]]:
    plan: list[tuple[Path, Path, str]] = []
    stats: Counter[str] = Counter()
    seen: set[Path] = set()
    language_dir = output / LANGUAGE_FOLDERS[language]
    for row in rows:
        character = safe_name(re.sub(r"<.*?>", "", row["character"]), "#Unknown")
        if row["battle"]:
            # Current indexes carry ``..._MediaID`` in the filename, so no
            # sidecar JSON is required.  Retain map fallback for old indexes.
            match = re.search(r"_(\d+)$", row["file"])
            media_ids = [int(match.group(1))] if match else battle_map.get(row["file"], {}).get("media_ids", [])
            if not media_ids:
                stats["battle_missing_media"] += 1
                continue
            for media_id in media_ids:
                source_root = battle_source or source
                src = source_root / f"{media_id}.wav"
                filename = safe_name(row["file"], "battle")
                if not match:
                    filename = f"{filename}_{media_id}"
                dst = language_dir / character / BATTLE_FOLDER / f"{filename}.wav"
                if dst not in seen:
                    plan.append((src, dst, clean_text(row["text"])))
                    seen.add(dst)
            continue
        if not row["hash"]:
            stats["normal_missing_hash"] += 1
            continue
        src = source / f"{row['hash']}.wav"
        dst = language_dir / character / f"{safe_name(row['file'], 'voice')}.wav"
        if dst not in seen:
            plan.append((src, dst, clean_text(row["text"])))
            seen.add(dst)
    return plan, stats


def execute(plan: list[tuple[Path, Path, str]], mode: str, dry_run: bool) -> Counter[str]:
    stats: Counter[str] = Counter()
    for src, dst, text in plan:
        if not src.is_file():
            stats["missing_source"] += 1
            continue
        stats["matched_source"] += 1
        if dry_run:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if mode == "cp":
            shutil.copy2(src, dst)
        else:
            shutil.move(src, dst)
        dst.with_suffix(".lab").write_text(text, encoding="utf-8")
        stats["written"] += 1
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="按语音索引整理 WAV；支持 battle MediaID 映射")
    parser.add_argument("-l", "--language", required=True, choices=LANGUAGE_FOLDERS)
    parser.add_argument("-i", "--index", type=Path)
    parser.add_argument("-src", "--source", type=Path, default=Path("./Data/wav"))
    parser.add_argument("-dst", "--output", type=Path, default=Path("./Data/sorted"))
    parser.add_argument("--battle-map", type=Path)
    parser.add_argument("--battle-source", type=Path)
    parser.add_argument("-m", "--mode", choices=("cp", "mv"), default="cp")
    parser.add_argument("--dry-run", action="store_true", help="只核对来源与目标，不创建目录、不复制、不移动")
    args = parser.parse_args()
    language = args.language.upper()
    index = args.index or Path("./Indexs") / f"{language}.xlsx"
    if not index.is_file():
        raise SystemExit(f"找不到索引：{index}")
    battle_map_path = args.battle_map
    if battle_map_path is None:
        battle_map_path = Path("./Maps") / language / "Voice_Maps" / "Battle_Event_Map.json"
    plan, preparation = make_plan(read_rows(index), args.source, args.output, language, load_battle_map(battle_map_path), args.battle_source)
    result = execute(plan, args.mode, args.dry_run)
    print(json.dumps({"dry_run": args.dry_run, "planned_files": len(plan), **preparation, **result}, ensure_ascii=False, indent=2))
    if args.dry_run:
        for src, dst, _ in plan[:10]:
            print(f"{src} -> {dst}")


if __name__ == "__main__":
    main()
