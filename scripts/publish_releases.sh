#!/bin/bash
# output/(쇼츠)·out/(롱폼)의 결과물을 GitHub Releases로 올림. 같은 태그가 있으면 교체.
set -e
shopt -s nullglob
D="$(TZ=Asia/Seoul date +%m/%d)"   # Release 제목 앞에 생성 날짜 → 목록에서 오늘 것 찾기 쉽게
mp3s=(output/voice_*.mp3)
if [ ${#mp3s[@]} -gt 0 ]; then
  gh release delete voice-samples -y --cleanup-tag 2>/dev/null || true
  gh release create voice-samples "${mp3s[@]}" --title "음성 샘플 (한국어 3 / 일본어 2)" --notes "edge-tts 무료 제공분 전체. 한국어: SunHi(여), InJoon(남), Hyunsu(남) / 일본어: Nanami(여), Keita(남)"
fi
for mp4 in output/*.mp4; do
  base="${mp4%.mp4}"; tag="$(basename "$base")"
  gh release delete "$tag" -y --cleanup-tag 2>/dev/null || true
  gh release create "$tag" "$mp4" "${base}_thumb.jpg" "$base.txt" \
    --title "[$D] $(sed -n 2p "$base.txt")" --notes-file "$base.txt"
done
for mp4 in out/day*_listening.mp4; do
  stem="${mp4%.mp4}"; n=$(basename "$stem" | sed -E 's/day([0-9]+)_listening/\1/')
  tag="longform_day$n"; files=("$mp4" "${stem}_description.txt")
  if [ -d "${stem}_tts_check" ]; then
    (cd out && zip -qr "$(basename "$stem")_tts_check.zip" "$(basename "$stem")_tts_check")
    files+=("${stem}_tts_check.zip")
  fi
  gh release delete "$tag" -y --cleanup-tag 2>/dev/null || true
  gh release create "$tag" "${files[@]}" --title "[$D] 롱폼 듣기 Day $n" --notes-file "${stem}_description.txt"
done
