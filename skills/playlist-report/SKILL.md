---
name: playlist-report
description: Spotify 플레이리스트(하나 또는 여러 개, 좋아요 곡 포함)를 분석해 장르 분포, 아티스트 편중, 중복곡을 요약한다. "내 플레이리스트 분석해줘", "어떤 장르를 많이 듣는지", "중복곡 있나" 같은 요청에 사용. 읽기 전용.
---

# 플레이리스트 분석 리포트

스크립트 경로 `<S>` = `${CLAUDE_PLUGIN_ROOT}/scripts` (비어 있으면 이 SKILL.md 기준 `../../scripts`)의 **절대경로로 치환해** 실행한다. 셸 변수는 호출 사이에 유지되지 않으니 쓰지 않는다. `~` 경로는 스크립트가 직접 펼친다.

1. `python "<S>/spotify.py" items "<플레이리스트>" [...] --out ~/.spotify-curator/work/report_tracks.json`
2. `python "<S>/tags.py" ~/.spotify-curator/work/report_tracks.json --out ~/.spotify-curator/work/report_tags.json`
3. `python "<S>/group.py" ~/.spotify-curator/work/report_tracks.json ~/.spotify-curator/work/report_tags.json --out ~/.spotify-curator/work/report_groups.json`
4. 출력 요약으로 리포트를 쓴다:
   - 총 곡 수, 장르 분포 표(곡 수, 비율), 상위 아티스트 10, 중복곡 수
   - 해석 2–3줄: 취향의 중심, 편중(한 아티스트가 10% 이상 등), 미분류 비율
   - 다음 행동 제안: 중복 정리, playlist-mix로 분할, playlist-extend로 약한 장르 보강
5. 중복곡 상세가 필요하면 `~/.spotify-curator/work/report_groups.json`의 `duplicates`만 읽어서 보여준다.
   중복 제거를 원하면: 기존 `items` 결과에서 중복을 뺀 uri 배열을 만들어 `replace --allow-change`로 반영(자동 백업, 사용자 확인 필수).

사용자가 공유할 페이지를 원하면 이 내용으로 아티팩트를 만든다. 기본은 터미널 표.
