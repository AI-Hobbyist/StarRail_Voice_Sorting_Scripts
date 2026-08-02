"""Merge one language's Star Rail voice XLSX indexes into a canonical workbook."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

COLUMNS = ["语音哈希", "语音文件名", "角色", "语音文本", "数据来源", "是否为战斗语音"]


def cell(row: pd.Series, index: int) -> str:
    value = row.iloc[index] if index < len(row) else ""
    return "" if pd.isna(value) else str(value)


def read_index(path: Path) -> list[dict[str, str]]:
    frame = pd.read_excel(path, dtype=object).fillna("")
    result = []
    battle_column = "是否为战斗语音" if "是否为战斗语音" in frame.columns else None
    source_column = "数据来源" if "数据来源" in frame.columns else None
    for _, row in frame.iterrows():
        # Position fallback keeps the historical four-column files usable even
        # when their legacy Chinese headers were saved with an old code page.
        result.append({
            "语音哈希": cell(row, 0),
            "语音文件名": cell(row, 1),
            "角色": cell(row, 2),
            "语音文本": cell(row, 3),
            "数据来源": str(row[source_column]) if source_column else "",
            "是否为战斗语音": "true" if battle_column and str(row[battle_column]).lower() == "true" else "",
        })
    return result


def merge_indexes(paths: list[Path]) -> tuple[list[dict[str, str]], dict[str, int]]:
    merged: dict[tuple[str, str, str], dict[str, str]] = {}
    total = 0
    for path in paths:
        for row in read_index(path):
            total += 1
            battle = row["是否为战斗语音"] == "true"
            key = ("battle" if battle else "voice", row["语音哈希"], row["语音文件名"])
            old = merged.get(key)
            if old is None:
                merged[key] = row
                continue
            # Preserve the first deterministic row but fill any missing fields;
            # a battle marker always wins over an empty legacy value.
            for column in COLUMNS:
                if not old[column] and row[column]:
                    old[column] = row[column]
            if battle:
                old["是否为战斗语音"] = "true"
    records = sorted(merged.values(), key=lambda row: (row["语音文件名"], row["语音哈希"]))
    return records, {"input_rows": total, "merged_rows": len(records), "duplicates_removed": total - len(records)}


def main() -> None:
    parser = argparse.ArgumentParser(description="从上级索引目录合并 XLSX 到本项目 Indexs")
    parser.add_argument("--source-index-dir", type=Path, required=True, help="上级索引文件夹")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "Indexs")
    parser.add_argument("--languages", nargs="+", default=["CHS", "EN", "JP", "KR"])
    args = parser.parse_args()
    source = args.source_index_dir
    if not source.is_dir():
        raise SystemExit(f"找不到上级索引目录：{source}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for item in args.languages:
        language = item.upper()
        inputs = sorted(source.glob(f"{language}*.xlsx"))
        if not inputs:
            print(f"[{language}] 未找到输入 XLSX，跳过")
            continue
        output = args.output_dir / f"{language}.xlsx"
        records, summary = merge_indexes(inputs)
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            pd.DataFrame(records, columns=COLUMNS).to_excel(writer, index=False, sheet_name="语音索引", freeze_panes=(1, 0))
            sheet = writer.sheets["语音索引"]
            sheet.auto_filter.ref = sheet.dimensions
            for column, width in zip("ABCDEF", (19, 58, 24, 70, 30, 16)):
                sheet.column_dimensions[column].width = width
        print(f"[{language}] {len(inputs)} 个文件：{summary['input_rows']:,} → {summary['merged_rows']:,}；{output}")


if __name__ == "__main__":
    main()
