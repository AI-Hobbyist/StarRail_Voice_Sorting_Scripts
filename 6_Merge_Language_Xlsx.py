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


def merge_indexes(paths: list[Path], existing: list[dict[str, str]] | None = None) -> tuple[list[dict[str, str]], dict[str, int]]:
    merged: dict[tuple[str, str, str], dict[str, str]] = {}
    # 增量基线：先载入已有输出——源文件中已删除的行会保留在结果里，
    # 但新输入里再次出现的同 key 行会用新内容覆盖更新。
    for row in existing or []:
        battle = row["是否为战斗语音"] == "true"
        key = ("battle" if battle else "voice", row["语音哈希"], row["语音文件名"])
        merged[key] = row
    kept = len(merged)
    total = 0
    added = 0
    updated = 0
    for path in paths:
        for row in read_index(path):
            total += 1
            battle = row["是否为战斗语音"] == "true"
            key = ("battle" if battle else "voice", row["语音哈希"], row["语音文件名"])
            if key not in merged:
                # 不存在的新行：补充进去。
                merged[key] = row
                added += 1
            else:
                # 同 key：用新输入的内容覆盖更新；多个源文件重复出现时后者胜出。
                merged[key] = row
                updated += 1
    records = sorted(merged.values(), key=lambda row: (row["语音文件名"], row["语音哈希"]))
    return records, {
        "input_rows": total,
        "existing_rows": kept,
        "added_rows": added,
        "updated_rows": updated,
        "merged_rows": len(records),
    }


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
        # 读取已有输出作为增量基线；不存在时从空开始。
        existing = read_index(output) if output.exists() else []
        records, summary = merge_indexes(inputs, existing)
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            pd.DataFrame(records, columns=COLUMNS).to_excel(writer, index=False, sheet_name="语音索引", freeze_panes=(1, 0))
            sheet = writer.sheets["语音索引"]
            sheet.auto_filter.ref = sheet.dimensions
            for column, width in zip("ABCDEF", (19, 58, 24, 70, 30, 16)):
                sheet.column_dimensions[column].width = width
        print(f"[{language}] {len(inputs)} 个文件：原有 {summary['existing_rows']:,} + 新增 {summary['added_rows']:,}（更新 {summary['updated_rows']:,}）→ 共 {summary['merged_rows']:,}；{output}")


if __name__ == "__main__":
    main()
