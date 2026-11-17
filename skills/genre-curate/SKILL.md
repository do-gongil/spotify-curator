---
name: genre-curate
description: 사용자가 지정한 기존 Spotify 플레이리스트들(또는 좋아요 곡)에서 비슷한 장르의 곡만 골라 새 플레이리스트를 만든다. "내 플레이리스트들에서 재즈만 모아줘", "힙합 곡만 뽑아서 새로 만들어줘" 같은 요청에 사용.
---

# 장르별 선별 → 새 플레이리스트

스크립트 경로 `<S>` = `${CLAUDE_PLUGIN_ROOT}/scripts` (비어 있으면 이 SKILL.md 기준 `../../scripts`)의 **절대경로로 치환해** 실행한다. 셸 변수는 호출 사이에 유지되지 않으니 쓰지 않는다. `~` 경로는 스크립트가 직접 펼친다.
작업 파일은 `~/.spotify-curator/work/`에 생긴다. 곡 목록 JSON을 통째로 읽지 말고 스크립트가 출력하는 요약만 사용한다.

1. 대상 확인: 사용자가 플레이리스트를 지정하지 않았으면 `python "<S>/spotify.py" playlists` 로 목록을 보여주고 고르게 한다.
   Web API로 폴더는 읽을 수 없으니 플레이리스트 이름으로 지정받는다. `liked` = 좋아요 곡. "(팔로우만)" 표시는 곡을 읽을 수 없다.
2. 수집: `python "<S>/spotify.py" items "<플레이리스트1>" "<플레이리스트2>" ... --out ~/.spotify-curator/work/curate_tracks.json`
3. 태그: `python "<S>/tags.py" ~/.spotify-curator/work/curate_tracks.json --out ~/.spotify-curator/work/curate_tags.json`
4. 그룹: `python "<S>/group.py" ~/.spotify-curator/work/curate_tracks.json ~/.spotify-curator/work/curate_tags.json --out ~/.spotify-curator/work/curate_groups.json`
5. `unclassified_artists`가 있으면 아는 범위에서 장르를 판단해
   `python "<S>/tags.py" --set "Artist=genre1,genre2" ...` 로 저장하고 3–4단계를 다시 실행한다. 모르는 아티스트는 추측하지 말고 unclassified로 둔다.
6. 장르별 곡 수를 표로 보여주고 어떤 장르(복수 가능)를 모을지, 플레이리스트 이름을 확인한다.
   요청 장르가 macro 장르와 정확히 맞지 않으면(예: "시티팝") group 결과의 원 태그를 기준으로 판단해 별도 uri 목록 JSON을 만든다.
7. 생성: `python "<S>/spotify.py" create "<이름>" ~/.spotify-curator/work/curate_groups.json --key "groups.<장르>" --description "<요약>"`
   여러 장르를 합칠 땐 uri 목록을 하나의 JSON 배열 파일로 합친 뒤 `--key` 없이 넘긴다.
8. 결과(곡 수, 링크)를 한 줄로 보고한다.

에러 대응: `로그인이 필요합니다` → `python "<S>/spotify.py" login` 안내. 403 → Dev Mode 앱의 사용자 등록(User Management)과 Premium 여부 확인 안내.
