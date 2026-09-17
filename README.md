# deskmate-voice

[deskmate](https://github.com/sysilion/deskmate) 가 받아 쓰는 **로컬 음성 번들**을 굽는다.
사람이 직접 받을 것은 없다 — 앱의 `설정 → 목소리` 에서 받아 간다.

## 왜 따로 있나

말하는 데 필요한 것은 실행 파일 하나와 모델 하나인데, 원본을 그대로 쓰면 **143MB**다.
음성 인식·VAD 실행 파일과 전 세계 언어의 발음 사전 18MB가 같이 들어 있기 때문이다.
여기서 쓰는 것만 남기면 **64MB**로 줄고, 앱은 자기 플랫폼 것 하나만 받으면 된다.

앱에 내장하지 않는 이유는 간단하다. deskmate 배포본이 4.7MB인데 번들이 64MB다.
음성을 쓰지 않는 사람이 그 값을 치를 이유가 없다.

## 무엇이 들어가나

| | |
| --- | --- |
| 엔진 | [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) (Apache-2.0) 의 `sherpa-onnx-offline-tts` 와 onnxruntime |
| 한국어 음성 | `vits-mimic3-ko_KO-kss_low` — [KSS 데이터셋](https://www.kaggle.com/datasets/bryanpark/korean-single-speaker-speech-dataset) 기반 단일 화자 |
| 발음 데이터 | espeak-ng 에서 **해당 언어분만** (18MB → 1.2MB) |

실시간의 7배쯤 빠르다. CPU만 쓰고 네트워크를 타지 않는다.

## 굽기

```sh
python tools/build-bundle.py --platform osx-arm64 --voice ko --out dist
python tools/write-manifest.py --dir dist --tag v1
```

플랫폼은 `osx-arm64` · `osx-x64` · `linux-x64` · `win-x64`.
태그를 밀면 GitHub Actions 가 넷을 모두 굽고 릴리스에 올린다.

`manifest.json` 하나에 주소·크기·해시가 적힌다. 앱은 그것만 읽는다 —
파일 이름을 앱에 박아 두면 번들 구성을 바꿀 때마다 앱을 새로 내야 한다.

## 라이선스

굽는 스크립트는 MIT. **담기는 것은 각자의 라이선스를 따른다** —
sherpa-onnx 는 Apache-2.0, espeak-ng 는 GPL-3.0, 음성 모델은 원본 배포처의 조건을 본다.
번들을 다시 배포한다면 그 조건을 확인할 것.
