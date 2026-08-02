"""Unpack PCK files and transcode all extracted WEM files to a flat WAV directory."""
from __future__ import annotations

import argparse
import multiprocessing
import subprocess
from collections import Counter, defaultdict
from os import cpu_count
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    class _NoProgress:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def update(self, *_args): pass
    def tqdm(iterable=None, **_kwargs):
        return iterable if iterable is not None else _NoProgress()

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools"


def find_wem_files(wem_root: Path) -> list[Path]:
    """Find WEMs recursively; localized banks live below e.g. chinese(prc)."""
    return sorted(path for path in wem_root.rglob("*") if path.is_file() and path.suffix.lower() == ".wem")


def wav_output_path(source: Path, wav_root: Path) -> Path:
    # Deliberately retain the historical flat output layout.  In particular,
    # chinese(prc)/123.wem becomes Data/wav/123.wav for battle sorting.
    return wav_root / f"{source.stem}.wav"


def unpack(pck_root: Path, wem_root: Path) -> int:
    pck_files = sorted(pck_root.rglob("*.pck"))
    for pck_file in tqdm(pck_files, desc="解包音频"):
        subprocess.run(
            [str(TOOLS / "quickbms.exe"), "-q", "-k", str(TOOLS / "wwise_pck_extractor.bms"), str(pck_file), str(wem_root)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    return len(pck_files)


def transcode_one(job: tuple[Path, Path]) -> str:
    source, destination = job
    if destination.is_file():
        return "existing"
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [str(TOOLS / "vgmstream-cli.exe"), "-o", str(destination), str(source)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return "converted" if completed.returncode == 0 and destination.is_file() else "failed"


def transcode_wems(process_count: int, wem_root: Path, wav_root: Path, dry_run: bool = False) -> Counter[str]:
    files = find_wem_files(wem_root)
    jobs = [(source, wav_output_path(source, wav_root)) for source in files]
    collisions: defaultdict[Path, list[Path]] = defaultdict(list)
    for source, destination in jobs:
        collisions[destination].append(source)
    duplicate_names = {destination: sources for destination, sources in collisions.items() if len(sources) > 1}
    if duplicate_names:
        sample = next(iter(duplicate_names.items()))
        raise RuntimeError(
            f"扁平 WAV 输出发生同名冲突：{sample[0].name}，例如 {sample[1][0]} 与 {sample[1][1]}"
        )
    summary: Counter[str] = Counter({"wem_files": len(files), "planned_wavs": len(jobs)})
    summary["nested_wems"] = sum(source.parent != wem_root for source in files)
    if dry_run:
        return summary
    if not jobs:
        return summary
    workers = process_count or cpu_count() or 1
    with tqdm(total=len(jobs), desc="转码音频") as progress:
        with multiprocessing.Pool(workers) as pool:
            for status in pool.imap_unordered(transcode_one, jobs):
                summary[status] += 1
                progress.update(1)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="解包 PCK 并递归转码 WEM 到平铺 WAV 目录")
    parser.add_argument("-p", "--pck", type=Path, default=Path("./Data/pcks"))
    parser.add_argument("-r", "--wem", type=Path, default=Path("./Data/raw"))
    parser.add_argument("-w", "--wav", type=Path, default=Path("./Data/wav"))
    parser.add_argument("-c", "--process-count", type=int, default=0)
    parser.add_argument("--skip-unpack", action="store_true", help="仅转码已有 WEM")
    parser.add_argument("--dry-run", action="store_true", help="仅统计递归发现的 WEM 与目标 WAV，不写文件")
    args = parser.parse_args()

    if not args.skip_unpack:
        args.pck.mkdir(parents=True, exist_ok=True)
        args.wem.mkdir(parents=True, exist_ok=True)
        unpacked = unpack(args.pck, args.wem)
        print(f"PCK 文件：{unpacked}")
    summary = transcode_wems(args.process_count, args.wem, args.wav, args.dry_run)
    print(dict(summary))
    if args.dry_run:
        for source in find_wem_files(args.wem)[:10]:
            print(f"{source} -> {wav_output_path(source, args.wav)}")


if __name__ == "__main__":
    main()
