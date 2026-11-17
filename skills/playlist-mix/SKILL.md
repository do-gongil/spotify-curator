---
name: playlist-mix
description: 한 Spotify 플레이리스트 안의 곡들을 비슷한 음악끼리 묶는다 — 유사 그룹별 하위 플레이리스트로 분할하거나, 원본을 비슷한 곡이 이어지도록 재정렬한다. "이 플레이리스트 장르별로 나눠줘", "비슷한 곡끼리 붙게 순서 정리해줘", "믹스해줘" 같은 요청에 사용.
---

# 플레이리스트 믹스 (분할 + 재정렬)

스크립트 경로 `<S>` = `${CLAUDE_PLUGIN_ROOT}/scripts` (비어 있으면 이 SKILL.md 기준 `../../scripts`)의 **절대경로로 치환해** 실행한다. 셸 변수는 호출 사이에 유지되지 않으니 쓰지 않는다. `~` 경로는 스크립트가 직접 펼친다.
Spotify 앱의 Mix(전환 효과) 기능은 API로 제어할 수 없다. 여기서 "믹스"는 유사도 기반 분할/정렬을 뜻한다.

1. `python "<S>/spotify.py" items "<플레이리스트>" --out ~/.spotify-curator/work/mix_tracks.json`
2. `python "<S>/tags.py" ~/.spotify-curator/work/mix_tracks.json --out ~/.spotify-curator/work/mix_tags.json`
3. `python "<S>/group.py" ~/.spotify-curator/work/mix_tracks.json ~/.spotify-curator/work/mix_tags.json --out ~/.spotify-curator/work/mix_groups.json`
4. `unclassified_artists`는 아는 범위에서 `tags.py --set`으로 보강 후 2–3단계 재실행(모르면 그대로 둠).
5. 장르별 곡 수를 보여주고 무엇을 할지 확인한다 (기본: 둘 다):
   - **분할**: 곡이 5곡 미만인 그룹은 가장 가까운 그룹에 합치거나 "기타"로 묶자고 제안.
     그룹별로 `python "<S>/spotify.py" create "<원본> · <장르>" ~/.spotify-curator/work/mix_groups.json --key "groups.<장르>"`
   - **재정렬**: 원본을 바꾸는 작업이므로 반드시 사용자 확인 후. 확인 시 알릴 것: 곡별 '추가한 날짜'가 지금 시각으로 바뀌며 백업으로도 복원되지 않음.
     replace는 정확한 플레이리스트 이름 또는 id만 받는다.
     `python "<S>/spotify.py" replace "<플레이리스트>" ~/.spotify-curator/work/mix_groups.json --key "mix_order"`
     (스크립트가 자동으로 백업하고, 곡 구성이 달라지면 거부한다. 출력된 되돌리기 명령을 사용자에게 알려준다.)
6. 생성된 플레이리스트와 재정렬 결과, 백업 경로를 보고한다.

장르 이름에 `.`이 들어가면 `--key`가 동작하지 않으므로 해당 그룹 uri를 별도 JSON 배열 파일로 저장해 넘긴다.
