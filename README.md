# 한국어 단어 쇼츠 + 롱폼 듣기 파이프라인 (일본인 학습자용)

큐에 넣어 둔 단어 JSON → 9:16 퀴즈형 쇼츠(mp4) 자동 생성 → **GitHub Releases에서 받아 직접 업로드**.
API 키 필요 없음 (콘텐츠는 Claude/ChatGPT 대화로 만들어 큐에 넣음, 음성은 무료 edge-tts).

> 기존 `japaneseword-shorts`(한국인 → 일본어)와 같은 파이프라인을 **방향만 뒤집은** 저장소입니다.
> 배우는 말 = **한국어**(큰 글씨 · 선희 음성), 설명하는 말 = **일본어**(뜻 · 인트로 · 자막 · 나나미 음성).

```
content/queue/vocab_001.json ─▶ Pillow 장면 ─▶ 여성 음성(한국어 단어 + 일본어 뜻) ─▶ ffmpeg mp4
                                                                              │
매일 08:03 KST GitHub Actions (+백업 실행) ─────────────────────────────────────────────┴─▶ Releases (mp4 + 썸네일 jpg + 제목/설명.txt)
                                                                                   └─▶ data/history.json (Day 번호, 중복 방지)
```

## 매일 자동 생성 (08:03 KST + 백업 실행)
- 쇼츠 1개: `content/queue/vocab_NNN.json` 순서대로 → Release `vocab_dayNNN`
- 왕초보 쇼츠 1개: `content/queue/basic_NNN.json` → Release `basic_dayNNN`
- 롱폼 1개: `longform/days/dayNN.json` (쇼츠 같은 Day 단어 + 단어당 예문 3개) → Release `longform_dayNN`
- 진행 상황은 `data/history.json`의 `vocab_day`, `basic_day`, `longform_day`. 큐가 3일치 이하로 남으면 Actions 로그에 경고.
- 롱폼 상세: [longform/README.md](longform/README.md)

## 쇼츠 영상 구성 (약 50초)
인트로 「今日の韓国語の単語10個。今日は何個わかるかな？」 → (한글 단어 + ？？？ → 3·2·1 카운트다운 → 정답: 가타카나 발음 + 한글 + 일본어 뜻 + 예문, 🔊 한국어·일본어) ×10 → 한 장 복습표 + 마무리 배너

**마무리 배너는 Day 홀짝으로 교대합니다** (`shorts/render.py`의 `cta_text`). 화면 글씨와 음성이 같이 바뀝니다.
- 홀수 Day → `チャンネル登録で毎日韓国語を勉強できます` (구독 유도)
- 짝수 Day → `今日は何個わかった？コメントで教えてね` (댓글 유도)

썸네일은 카테고리+개수(`韓国語の単語 / 10個`)를 유지합니다 — 피드에서 0.3초 안에 "한국어 학습 영상이고 10개짜리"를 읽히게 하는 역할이라, 도전 문구는 음성 인트로와 마무리 배너 쪽에 뒀습니다.

왕초보(`basic`) 시리즈는 가타카나 발음을 처음부터 보여주고 **뜻만** 묻습니다 (한글 읽기 부담 ↓).

## 단어 JSON 형식
```json
{
  "theme": "カフェで",
  "hook": "주문",
  "words": [
    {"word": "주문", "reading": "チュムン", "meaning": "注文",
     "example": "커피를 주문할게요.", "example_ja": "コーヒーを注文します。"}
  ]
}
```
| 필드 | 뜻 | 쓰이는 곳 |
|---|---|---|
| `word` | 한국어 단어 | 화면 큰 글씨 · 한국어 음성(선희)이 읽음 |
| `reading` | **가타카나 발음** | 정답 화면 위쪽 작은 글씨 · 복습표 |
| `meaning` | 일본어 뜻 | 정답 화면 · 일본어 음성(나나미)이 읽음 |
| `example` | 한국어 예문 | 정답 화면 카드 |
| `example_ja` | 일본어 번역 | 정답 화면 카드 (회색) |
| `theme` | 일본어 주제 | 썸네일 해시태그 · 제목 |
| `hook` | 썸네일에 크게 걸 단어 (생략 시 가장 긴 단어) | 썸네일 |
| `series` | `"basic"`이면 왕초보 시리즈 | 디자인·제목·태그 |

가타카나 표기는 일본 한국어 교재의 관례를 따릅니다: 어두 평음 ㄱㄷㅂㅈ = 무성(カ·タ·パ·チャ), 어중 = 유성(ガ·ダ·バ·ジャ), 경음 ㄲㄸㅃㅉㅆ = 촉음(ッカ·ッタ…), 받침 ㄹ = ル, ㅇ/ㄴ = ン, ㄱ/ㅂ = ッ·プ.

## 매일 하는 일 (2분)
1. PC에서 다운로드 스크립트 더블클릭 (아래 참고) — 또는 저장소 **Releases**에서 직접 받기
2. 유튜브 앱 → 쇼츠 업로드 → 같은 Release 본문의 제목/설명/태그 복사해서 붙여넣기

## 내 PC로 영상 받기 (더블클릭)
GitHub에서 만들어진 영상 중 **아직 안 받은 것만** 골라 PC 폴더에 저장합니다. Day별 폴더에 mp4 · 썸네일 · 제목/설명 txt가 들어갑니다.

| | Windows | Mac |
|---|---|---|
| 1. GitHub CLI 설치 (한 번) | 명령 프롬프트: `winget install GitHub.cli` | 터미널: `brew install gh` |
| 2. 스크립트 받기 | `download/download_windows.bat` + `download/download.ps1` (같은 폴더에) | `download/download_mac.command` |
| 3. 실행 | `download_windows.bat` 더블클릭 | `download_mac.command` 더블클릭 (막히면 터미널에서 `bash download_mac.command`) |
| 저장 위치 | `내 PC\동영상\korean-shorts\vocab_dayNNN\` | `~/Movies/korean-shorts/vocab_dayNNN/` |

처음 실행할 때 한 번 GitHub 로그인 창이 뜹니다(브라우저에서 코드 입력). 이후로는 더블클릭만 하면 됩니다.

## 큐 채우기 (2주에 한 번)
Claude에게 이렇게 요청하면 됩니다 (Claude Code 세션이면 파일까지 만들어서 push):
> 한국어 쇼츠 큐에 다음 14일치 단어 넣어줘. TOPIK 초급, 주제별 10개, 기존 단어 중복 없이, 가타카나 발음과 일본어 뜻·예문까지.

직접 넣을 땐 `content/queue/vocab_004.json` 처럼 번호 순으로, 형식은 `content/samples/vocab_sample.json` 참고.
넣은 뒤 `python -m shorts check` 로 형식/중복 검사. 큐가 3일치 이하로 남으면 Actions 로그에 경고가 뜹니다.

## 로컬 실행
```bash
sudo apt install ffmpeg fonts-noto-cjk      # mac: brew install ffmpeg
pip install -r requirements.txt
python -m shorts vocab --file content/samples/vocab_sample.json   # 테스트 (기록 안 남김)
python -m shorts vocab              # 큐에서 1개 렌더 → output/
python -m shorts vocab --count 7    # 일주일치 한 번에
python -m shorts basic              # 왕초보 1개
python -m shorts check              # 큐 형식/중복 검사
```

## 설정 (Settings → Secrets and variables → Actions → Variables, 모두 선택)
| 이름 | 기본값 | 설명 |
|---|---|---|
| `VOICE_KO` | `ko-KR-SunHiNeural` | 한국어 여성 음성(단어 읽기). 다른 여성 음성: `ko-KR-JiMinNeural`, `ko-KR-SeoHyeonNeural`, `ko-KR-YuJinNeural` |
| `VOICE_JA` | `ja-JP-NanamiNeural` | 일본어 여성 음성(뜻·인트로). 다른 여성 음성: `ja-JP-AoiNeural`(밝음), `ja-JP-MayuNeural`, `ja-JP-ShioriNeural` |
| `CHANNEL_NAME` | `毎日韓国語` | 설명란 표기 |
| `TOPIK_LEVEL` | `初級` | 태그 표기 (TOPIK 1~2급) |

수동 실행: Actions → *daily-shorts* → Run workflow (kind, count 지정 가능).
음성 미리 듣기: kind에 `voices` 입력 → Releases의 *음성 샘플* 에서 mp3 재생.

## 썸네일
첫 장면(인트로)이 곧 썸네일입니다. 영상과 함께 `*_thumb.jpg`(1080×1920)로 저장되며, 눈이 편한 파스텔 5색이 Day마다 순환하고 레이아웃은 고정이라 채널 그리드에서 시리즈로 보입니다.
업로드 시 Release의 `_thumb.jpg`를 썸네일로 지정하거나, 앱에서 첫 프레임을 고르면 같은 디자인이 됩니다.
가운데 크게 들어가는 단어는 가장 긴 단어가 자동 선택되고, JSON에 `"hook": "주문"`으로 지정할 수도 있습니다.

## 커스터마이즈
- 색/폰트/음성 속도/뜻 읽기 끄기: `shorts/config.py` (`TTS_RATE`, `READ_MEANING`)
- 장면 길이·구성: `shorts/video.py` `build_scenes`
- 디자인: `shorts/render.py`
- 제목/설명/태그: `shorts/meta.py`
- 마무리 배너 문구·교대 규칙: `shorts/render.py` (`CTA_TEXT`, `CTA_TEXT_ALT`, `cta_text`)
- 문법 쇼츠(`grammar`)도 코드에 남아 있음 — `content/queue/grammar_*.json` 넣고 kind=grammar로 실행 (형식은 `content/samples/grammar_sample.json`)
