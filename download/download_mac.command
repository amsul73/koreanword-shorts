#!/bin/bash
# 새로 생성된 쇼츠 영상을 내 Mac으로 받기 (더블클릭 실행)
REPO="amsul73/koreanword-shorts"
DEST="${DEST:-$HOME/Movies/korean-shorts}"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI(gh)가 설치되어 있지 않습니다."
  echo "터미널에서 다음을 실행한 뒤 다시 시도하세요:  brew install gh"
  read -r -p "엔터를 누르면 닫힙니다"; exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "처음 한 번 GitHub 로그인이 필요합니다. 브라우저 안내를 따라주세요."
  gh auth login --hostname github.com --git-protocol https --web
fi

mkdir -p "$DEST"
new=0
for t in $(gh release list --repo "$REPO" --limit 200 --json tagName --jq '.[].tagName' | grep -E '^(vocab|basic|grammar|longform)_day'); do
  ls "$DEST/$t"/*.mp4 >/dev/null 2>&1 && continue
  if gh release download "$t" --repo "$REPO" --dir "$DEST/$t" --clobber; then
    echo "받음: $t"; new=$((new + 1))
  fi
done
echo ""
echo "새 영상 ${new}개  /  저장 폴더: $DEST"
[ "$new" -gt 0 ] && command -v open >/dev/null && open "$DEST"
exit 0
