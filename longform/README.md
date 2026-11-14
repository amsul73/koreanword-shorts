# 롱폼: 한국어 단어 듣기 반복 영상 (일본인 학습자용)

쇼츠와 같은 단어로 "틀어두고 듣는" 1920×1080 영상을 만듭니다. 배경은 눈이 편한 오프화이트(#F6F4EF), 강조(hl)는 노란 형광펜.

## 흐름
타이틀 + 일본어 인트로 → 단어마다 [단어 카드: 한국어 → 일본어 뜻 → 한국어 느리게] → 예문 3개
→ 예문마다 [일본어 문장+음성 → 생각 시간 카운트다운 → 한국어 문장(형광펜)+가타카나 발음 → 선희 → 1초 → 인준(-15%)]
→ 복습 화면 + 단어/뜻 음성. 한글은 표음문자라 단어 카드 음성은 `word`(한글) 그대로 읽습니다.

## 실행
```bash
python longform/make_listening_video.py longform/days/day01.json            # mp4 + description.txt + 음성 점검 폴더
python longform/make_listening_video.py longform/days/                       # 폴더 안 전부 (배치)
python longform/make_listening_video.py longform/days/day01.json --check     # 검증만 (hl 포함 여부, 누락 필드, 너무 긴 문장)
python longform/make_listening_video.py longform/days/day01.json --preview   # 화면 이미지만
옵션: --tts dummy (무음 테스트), --loops N, --think 초, --out 폴더
```
GitHub에서: Actions → **longform** → Run workflow → Releases의 `longform_dayNN`.

## 출력
- `dayNN_listening.mp4`
- `dayNN_listening_description.txt` — 유튜브 설명란용 (일본어, 챕터 포함)
- `dayNN_listening_tts_check/` — 숫자·단어카드 음성만 모은 점검용 wav + `list.txt`

## JSON 형식 (`days/day01.json`)
```json
{"day": 1, "theme": "朝のルーティン", "words": [
  {"word": "일어나다", "reading": "イロナダ", "meaning": "起きる", "examples": [
    {"ko": "매일 아침 6시에 일어나요.", "reading": "メイル アチム ヨソッシエ イロナヨ",
     "ja": "毎朝6時に起きます。", "hl": "일어나요"}]}]}
```
- `ko` 한국어 문장 (화면 메인 · 선희/인준 음성) · `reading` 그 문장의 가타카나 발음 · `ja` 일본어 번역 (문제 화면 · 나나미 음성) · `hl` 형광펜 칠할 부분 (`ko` 안에 반드시 존재)
