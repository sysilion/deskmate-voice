#!/usr/bin/env python3
"""deskmate 가 받아 쓸 음성 번들 하나를 굽는다.

sherpa-onnx 배포본과 음성 모델에서 **말하는 데 필요한 것만** 남긴다. 둘 다 그대로
쓰면 143MB인데, 대부분은 쓰지 않는 것이다 — 음성 인식·VAD 실행 파일, 그리고 전
세계 언어의 발음 사전 18MB.

  python tools/build-bundle.py --platform osx-arm64 --out dist

남기는 것:
  bin/          말하는 실행 파일 하나
  lib/          그 실행 파일이 실제로 링크하는 라이브러리만
  espeak-ng-data/  이 음성이 쓰는 언어 사전과 공용 표만
  *.onnx, tokens.txt, *.onnx.json
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

SHERPA_VERSION = "v1.13.8"
SHERPA_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
MODEL_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models"

# 플랫폼마다 배포본 이름과 라이브러리 확장자가 다르다.
PLATFORMS = {
    "osx-arm64": {
        "asset": f"sherpa-onnx-{SHERPA_VERSION}-osx-arm64-shared.tar.bz2",
        "exe": "sherpa-onnx-offline-tts",
        "libs": ["libonnxruntime.dylib"],
    },
    "osx-x64": {
        "asset": f"sherpa-onnx-{SHERPA_VERSION}-osx-x64-shared.tar.bz2",
        "exe": "sherpa-onnx-offline-tts",
        "libs": ["libonnxruntime.dylib"],
    },
    "linux-x64": {
        "asset": f"sherpa-onnx-{SHERPA_VERSION}-linux-x64-shared.tar.bz2",
        "exe": "sherpa-onnx-offline-tts",
        "libs": ["libonnxruntime.so"],
    },
    "win-x64": {
        "asset": f"sherpa-onnx-{SHERPA_VERSION}-win-x64-shared-MD-Release.tar.bz2",
        "exe": "sherpa-onnx-offline-tts.exe",
        "libs": ["onnxruntime.dll", "sherpa-onnx-c-api.dll", "sherpa-onnx-cxx-api.dll"],
    },
}

# 음성. 언어마다 한 줄.
VOICES = {
    "ko": {
        "archive": "vits-mimic3-ko_KO-kss_low.tar.bz2",
        "model": "ko_KO-kss_low.onnx",
        # espeak 가 이 언어에 쓰는 사전. 나머지 언어 사전은 버린다.
        "dicts": ["ko_dict"],
    },
}

# 어떤 언어를 쓰든 있어야 하는 공용 표. 이게 빠지면 실행은 되고 소리가 안 나온다.
ESPEAK_COMMON = ["phontab", "phondata", "phonindex", "intonations"]


def fetch(url: str, into: Path) -> Path:
    into.parent.mkdir(parents=True, exist_ok=True)
    if into.exists():
        print(f"  이미 받아 둠: {into.name}")
        return into
    print(f"  받는 중: {url}")
    urllib.request.urlretrieve(url, into)
    return into


def unpack(archive: Path, into: Path) -> Path:
    into.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        tar.extractall(into, filter="data")
    # 압축 파일은 폴더 하나를 품고 있다.
    roots = [p for p in into.iterdir() if p.is_dir()]
    return roots[0] if len(roots) == 1 else into


def copy_espeak(source: Path, target: Path, dicts: list[str]) -> None:
    """이 음성이 쓰는 것만 옮긴다. 전 언어를 옮기면 18MB가 된다."""
    target.mkdir(parents=True, exist_ok=True)
    for name in ESPEAK_COMMON + dicts:
        found = source / name
        if not found.exists():
            raise SystemExit(f"espeak 데이터에 {name} 이 없다: {source}")
        shutil.copy2(found, target / name)
    # `lang/` 은 언어 이름을 푸는 표라 통째로 둔다. 작다.
    if (source / "lang").is_dir():
        shutil.copytree(source / "lang", target / "lang", dirs_exist_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platform", required=True, choices=sorted(PLATFORMS))
    ap.add_argument("--voice", default="ko", choices=sorted(VOICES))
    ap.add_argument("--out", default="dist")
    ap.add_argument("--cache", default=".cache")
    args = ap.parse_args()

    plat = PLATFORMS[args.platform]
    voice = VOICES[args.voice]
    cache = Path(args.cache)
    out = Path(args.out)
    work = cache / "work" / f"{args.platform}-{args.voice}"
    shutil.rmtree(work, ignore_errors=True)

    print(f"[{args.platform} / {args.voice}]")
    sherpa = unpack(
        fetch(f"{SHERPA_URL}/{SHERPA_VERSION}/{plat['asset']}", cache / plat["asset"]),
        work / "sherpa",
    )
    model = unpack(
        fetch(f"{MODEL_URL}/{voice['archive']}", cache / voice["archive"]),
        work / "model",
    )

    stage = work / "bundle"
    (stage / "bin").mkdir(parents=True)
    (stage / "lib").mkdir(parents=True)

    exe = sherpa / "bin" / plat["exe"]
    if not exe.exists():
        raise SystemExit(f"실행 파일이 없다: {exe}")
    shutil.copy2(exe, stage / "bin" / plat["exe"])

    for lib in plat["libs"]:
        found = next(sherpa.rglob(lib), None)
        if found is None:
            raise SystemExit(f"라이브러리가 없다: {lib}")
        shutil.copy2(found, stage / "lib" / lib)

    copy_espeak(model / "espeak-ng-data", stage / "espeak-ng-data", voice["dicts"])
    for name in (voice["model"], voice["model"] + ".json", "tokens.txt"):
        shutil.copy2(model / name, stage / name)

    # 앱이 무엇을 부르면 되는지 적어 둔다. 파일 이름을 앱에 박아 두지 않게 한다.
    (stage / "voice.json").write_text(
        json.dumps(
            {
                "version": 1,
                "platform": args.platform,
                "voice": args.voice,
                "engine": "sherpa-onnx",
                "engineVersion": SHERPA_VERSION,
                "exe": f"bin/{plat['exe']}",
                "libDir": "lib",
                "model": voice["model"],
                "tokens": "tokens.txt",
                "dataDir": "espeak-ng-data",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    out.mkdir(parents=True, exist_ok=True)
    name = f"voice-{args.voice}-{args.platform}.tar.gz"
    archive = out / name
    # 재현 가능하게: 시각과 소유자를 지운다. 같은 입력이면 같은 결과다.
    with tarfile.open(archive, "w:gz") as tar:
        for path in sorted(stage.rglob("*")):
            info = tar.gettarinfo(path, arcname=str(path.relative_to(stage)))
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            if path.is_file():
                with path.open("rb") as fh:
                    tar.addfile(info, fh)
            else:
                tar.addfile(info)

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    size = archive.stat().st_size
    print(f"  -> {name}  {size / 1048576:.1f}MB  sha256:{digest[:16]}…")
    (out / f"{name}.sha256").write_text(f"{digest}  {name}\n", encoding="utf-8")
    return


if __name__ == "__main__":
    sys.exit(main())
