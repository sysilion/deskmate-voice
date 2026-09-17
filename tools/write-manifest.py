#!/usr/bin/env python3
"""구운 번들들을 한 장의 목록으로 적는다.

앱은 이 파일 하나만 읽고 자기 플랫폼 것을 골라 받는다. 파일 이름과 주소를 앱에
박아 두면 번들 구성을 바꿀 때마다 앱을 새로 내야 한다.
"""

import argparse
import hashlib
import json
from pathlib import Path

REPO = "sysilion/deskmate-voice"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="dist")
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()

    out = Path(args.dir)
    base = f"https://github.com/{REPO}/releases/download/{args.tag}"

    bundles = []
    for path in sorted(out.glob("voice-*.zip")):
        # voice-<음성>-<플랫폼>.zip
        voice, platform = path.name[len("voice-") : -len(".zip")].split("-", 1)
        bundles.append(
            {
                "voice": voice,
                "platform": platform,
                "file": path.name,
                "url": f"{base}/{path.name}",
                "size": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    manifest = {"version": 1, "tag": args.tag, "bundles": bundles}
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(bundles)}개 번들을 적었다")


if __name__ == "__main__":
    main()
