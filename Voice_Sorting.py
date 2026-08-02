"""Self-contained Star Rail voice pipeline: unpack, transcode, sort, classify, clean, statistics."""
from __future__ import annotations
import argparse
import html
import json
import re
import shutil
import subprocess
import wave
from collections import Counter, defaultdict
from multiprocessing import Pool
from os import cpu_count
from pathlib import Path
from typing import Any
from openpyxl import load_workbook
import pandas as pd
ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / 'tools'
LANG = {'CHS': '中文 - Chinese', 'JP': '日语 - Japanese', 'EN': '英语 - English', 'KR': '韩语 - Korean'}
SHEET = {'CHS': '中文', 'JP': '日语', 'EN': '英语', 'KR': '韩语'}
CATS = {'战斗语音 - Battle': 8, '怪物语音 - Monster': 11, '其它语音 - Others': 14, '带变量语音 - Placeholder': 17, '多人对话语音 - Conversation': 20}
INVALID = re.compile('[<>:"/\\\\|?*]')
TAG = re.compile('<.*?>')

def find_wems(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob('*')
        if path.is_file() and path.suffix.lower() == '.wem'
    )

def wav_path(wem: Path, wav: Path) -> Path:
    return wav / f'{wem.stem}.wav'

def unpack(pcks: Path, wems: Path) -> int:
    files = sorted(pcks.rglob('*.pck'))
    for item in files:
        subprocess.run(
            [
                str(TOOLS / 'quickbms.exe'),
                '-q',
                '-k',
                str(TOOLS / 'wwise_pck_extractor.bms'),
                str(item),
                str(wems),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    return len(files)

def _convert(job: tuple[Path, Path]) -> str:
    source, dest = job
    if dest.is_file():
        return 'existing'
    dest.parent.mkdir(parents=True, exist_ok=True)
    done = subprocess.run(
        [str(TOOLS / 'vgmstream-cli.exe'), '-o', str(dest), str(source)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return 'converted' if done.returncode == 0 and dest.is_file() else 'failed'

def transcode(wems: Path, wav: Path, dry: bool) -> Counter[str]:
    files = find_wems(wems)
    jobs = [(p, wav_path(p, wav)) for p in files]
    names = defaultdict(list)
    for source, dest in jobs:
        names[dest].append(source)
    bad = [(dest, items) for dest, items in names.items() if len(items) > 1]
    if bad:
        raise RuntimeError(f'平铺 WAV 同名冲突：{bad[0][0].name}')
    result = Counter(wem_files=len(files), planned_wavs=len(jobs), nested_wems=sum((p.parent != wems for p in files)))
    if not dry and jobs:
        with Pool(cpu_count() or 1) as pool:
            for status in pool.imap_unordered(_convert, jobs):
                result[status] += 1
    return result

def text(value: Any) -> str:
    return '' if pd.isna(value) else str(value)

def safe(value: str, fallback: str) -> str:
    return INVALID.sub('_', value).strip().rstrip('.') or fallback

def clean(value: str) -> str:
    return html.unescape(TAG.sub('', value)).replace('\n', ' ').strip()

def read_index(path: Path) -> list[dict[str, Any]]:
    frame = pd.read_excel(path, dtype=object).fillna('')
    battle = '是否为战斗语音' if '是否为战斗语音' in frame.columns else None
    result = []
    for _, r in frame.iterrows():
        get = lambda i: text(r.iloc[i]) if i < len(r) else ''
        result.append({'hash': get(0), 'file': get(1), 'character': get(2), 'label': get(3), 'battle': bool(battle and text(r[battle]).lower() == 'true')})
    return result

def sorting_plan(
    rows: list[dict[str, Any]],
    source: Path,
    output: Path,
    language: str,
    ) -> tuple[list[tuple[Path, Path, str]], Counter[str]]:
    plan = []
    stats = Counter()
    seen = set()
    base = output / LANG[language]
    for row in rows:
        speaker = safe(TAG.sub('', row['character']), '#Unknown')
        if row['battle']:
            match = re.search('_(\\d+)$', row['file'])
            if not match:
                stats['battle_missing_media'] += 1
                continue
            media = match.group(1)
            src = source / f'{media}.wav'
            dst = base / speaker / '战斗语音 - Battle' / f"{safe(row['file'], 'battle')}.wav"
        else:
            if not row['hash']:
                stats['normal_missing_hash'] += 1
                continue
            src = source / f"{row['hash']}.wav"
            dst = base / speaker / f"{safe(row['file'], 'voice')}.wav"
        if dst not in seen:
            plan.append((src, dst, clean(row['label'])))
            seen.add(dst)
    return (plan, stats)

def execute(plan: list[tuple[Path, Path, str]], mode: str, dry: bool) -> Counter[str]:
    result = Counter()
    for src, dst, label in plan:
        if not src.is_file():
            result['missing_source'] += 1
            continue
        result['matched_source'] += 1
        if dry:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst) if mode == 'cp' else shutil.move(src, dst)
        dst.with_suffix('.lab').write_text(label, encoding='utf-8')
        result['written'] += 1
    return result

def classify(source: Path, target: Path, language: str, routes: dict[str, str], dry: bool) -> Counter[str]:
    result = Counter()
    base = source / LANG[language]
    if not base.is_dir():
        return result
    for lab in base.rglob('*.lab'):
        wav = lab.with_suffix('.wav')
        rel = lab.relative_to(base)
        category = routes.get(lab.name)
        dst = target / LANG[language] / (Path(category) / lab.name if category else rel)
        if not wav.is_file():
            result['missing_wav'] += 1
            continue
        result['planned'] += 1
        if not dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(lab, dst)
            shutil.move(wav, dst.with_suffix('.wav'))
            result['moved'] += 1
    return result

def clean_labels(root: Path, dry: bool) -> Counter[str]:
    result = Counter()
    for lab in root.rglob('*.lab'):
        before = lab.read_text(encoding='utf-8')
        after = clean(before)
        if before != after:
            result['html_labels'] += 1
            if not dry:
                lab.write_text(after, encoding='utf-8')
    return result

def duration(path: Path) -> float:
    try:
        with wave.open(str(path), 'rb') as f:
            return f.getnframes() / f.getframerate() / 86400
    except (wave.Error, EOFError):
        return 0.0

def stat_rows(dataset: Path, language: str) -> list[list[Any]]:
    root = dataset / LANG[language]
    rows = []
    if not root.is_dir():
        return rows
    for speaker in sorted((p for p in root.iterdir() if p.is_dir())):
        wavs = list(speaker.rglob('*.wav'))
        labs = list(speaker.rglob('*.lab'))
        row = [speaker.name, 0, 0, 0.0, len(wavs), len(labs), sum(map(duration, wavs)), '|'] + [0] * 15
        plain = list(speaker.glob('*.wav'))
        plainlab = list(speaker.glob('*.lab'))
        row[1:4] = [len(plain), len(plainlab), sum(map(duration, plain))]
        for folder, index in CATS.items():
            path = speaker / folder
            ws = list(path.rglob('*.wav')) if path.is_dir() else []
            ls = list(path.rglob('*.lab')) if path.is_dir() else []
            row[index:index + 3] = [len(ws), len(ls), sum(map(duration, ws))]
        rows.append(row)
    return rows

def statistics(template: Path, dataset: Path, language: str, game: str, version: str, outdir: Path, dry: bool) -> Path:
    output = outdir / f'{game}_{version}_数据统计.xlsx'
    if dry:
        return output
    book = load_workbook(template)
    ws = book[SHEET[language]]
    table = next(iter(ws.tables.values()))
    rows = stat_rows(dataset, language)
    for r, row in enumerate(rows, 2):
        for c, value in enumerate(row, 1):
            ws.cell(r, c, value)
    table.ref = f'A1:W{len(rows) + 1}'
    outdir.mkdir(parents=True, exist_ok=True)
    book.save(output)
    return output

def main() -> None:
    p = argparse.ArgumentParser(description='完全内置的星穹铁道语音处理流水线')
    p.add_argument('-l', '--language', required=True, choices=LANG)
    p.add_argument('--pck', type=Path, default=ROOT / 'Data/pcks')
    p.add_argument('--wem', type=Path, default=ROOT / 'Data/raw')
    p.add_argument('--wav', type=Path, default=ROOT / 'Data/wav')
    p.add_argument('--index', type=Path)
    p.add_argument('--sorted', type=Path, default=ROOT / 'Data/sorted')
    p.add_argument('--final', type=Path, default=ROOT / 'Data/second_sorted')
    p.add_argument('--game', default='星穹铁道')
    p.add_argument('--version', default='4.4')
    p.add_argument('--stats-dir', type=Path, default=ROOT)
    p.add_argument('--template', type=Path, default=ROOT / '数据统计_模板.xlsx')
    p.add_argument('--mode', choices=('cp', 'mv'), default='cp')
    p.add_argument('--skip-unpack', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    lang = a.language.upper()
    if not a.skip_unpack:
        a.pck.mkdir(parents=True, exist_ok=True)
        a.wem.mkdir(parents=True, exist_ok=True)
        print('解包 PCK', unpack(a.pck, a.wem))
    print('转码', dict(transcode(a.wem, a.wav, a.dry_run)))
    index = a.index or ROOT / 'Indexs' / f'{lang}.xlsx'
    plan, pre = sorting_plan(
        read_index(index),
        a.wav,
        a.sorted,
        lang,
    )
    print('整理', dict(pre), dict(execute(plan, a.mode, a.dry_run)))
    routes = json.loads((ROOT / 'Data/Sorted.json').read_text(encoding='utf-8')) if (ROOT / 'Data/Sorted.json').is_file() else {}
    print('二次整理', dict(classify(a.sorted, a.final, lang, routes, a.dry_run)))
    print('清理标签', dict(clean_labels(a.final / LANG[lang], a.dry_run)))
    print('统计表', statistics(a.template, a.final, lang, a.game, a.version, a.stats_dir, a.dry_run))
if __name__ == '__main__':
    main()
