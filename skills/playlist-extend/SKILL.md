---
name: playlist-extend
description: 기존 Spotify 플레이리스트의 분위기·장르에 맞는 새 곡을 추천해 추가한다. "이 플레이리스트에 비슷한 곡 10개 더 넣어줘", "이 느낌으로 확장해줘" 같은 요청에 사용.
---

# 비슷한 곡으로 플레이리스트 확장

스크립트 경로 `<S>` = `${CLAUDE_PLUGIN_ROOT}/scripts` (비어 있으면 이 SKILL.md 기준 `../../scripts`)의 **절대경로로 치환해** 실행한다. 셸 변수는 호출 사이에 유지되지 않으니 쓰지 않는다. `~` 경로는 스크립트가 직접 펼친다.

1. 프로필 만들기:
   `python "<S>/spotify.py" items "<플레이리스트>" --out ~/.spotify-curator/work/ext_tracks.json`
   `python "<S>/tags.py" ~/.spotify-curator/work/ext_tracks.json --out ~/.spotify-curator/work/ext_tags.json`
   `python "<S>/group.py" ~/.spotify-curator/work/ext_tracks.json ~/.spotify-curator/work/ext_tags.json --out ~/.spotify-curator/work/ext_groups.json`
   요약의 장르 분포·상위 아티스트와 `~/.spotify-curator/work/ext_tags.json`의 상위 태그로 플레이리스트 성격을 2줄로 정리한다.
2. 추가 곡 수(기본 10)와 방향(같은 아티스트 허용 여부, 특정 장르 강화)을 확인한다. 기본: 기존 아티스트의 다른 곡 30% 이하, 나머지는 비슷한 결의 다른 아티스트.
3. 후보를 목표의 약 1.5배, `Artist - Title`로 `~/.spotify-curator/work/ext_queries.txt`에 쓴다. 실존을 확신하는 곡만.
   Spotify 표시 표기로 쓴다: 공식 영어 제목이 있으면 영어 제목(예: `LEE HI - BREATHE`). 원어 제목은 점수가 낮게 나온다.
4. `python "<S>/spotify.py" search --file ~/.spotify-curator/work/ext_queries.txt --out ~/.spotify-curator/work/ext_search.json`
   - confidence ≥ 0.8 채택 (0.6–0.8은 매치를 보고 판단).
   - 0.6 미만이라도 아티스트가 같고 제목이 공식 번역/표기 차이임을 확신하면 채택. 리믹스·라이브·다른 아티스트 곡은 제외.
   - `~/.spotify-curator/work/ext_tracks.json`에 이미 있는 uri와 같은 곡(이름+아티스트)은 제외한다. 이 비교는 짧은 python 한 줄로 하고 파일을 통째로 읽지 않는다.
5. 추가 목록을 보여주고 확인받은 뒤 uri 배열을 `~/.spotify-curator/work/ext_uris.json`에 저장하고
   `python "<S>/spotify.py" add "<플레이리스트>" ~/.spotify-curator/work/ext_uris.json`
6. 추가된 곡 수를 보고하고, 흐름을 원하면 playlist-mix의 재정렬을 제안한다.

참고: Spotify recommendations/related-artists API는 신규 앱에서 사용할 수 없어 Claude의 추천 + search 검증 방식을 쓴다.
