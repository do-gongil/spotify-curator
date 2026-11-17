---
name: setup
description: spotify-curator 최초 설정과 문제 진단. Spotify Client ID·Last.fm 키 저장, 로그인, 권한 점검을 단계별로 안내한다. "spotify-curator 설정해줘", "스포티파이 연결이 안 돼", "403 떠" 같은 요청이나 다른 스킬이 로그인/키 오류로 막혔을 때 사용. Also for "set up spotify-curator", "spotify login fails".
---

# 설정 / 진단

`<S>` = `${CLAUDE_PLUGIN_ROOT}/scripts` (비어 있으면 이 SKILL.md 기준 `../../scripts`)의 **절대경로**. `python`이 없으면 `python3`.

1. 먼저 `python "<S>/spotify.py" doctor` 실행. "준비 완료"면 끝.
2. `Spotify Client ID`가 FAIL이면 사용자에게 안내(링크·Redirect URI는 `setup` 출력에 있음):
   - https://developer.spotify.com/dashboard → Create app → API: Web API, Redirect URI `http://127.0.0.1:8888/callback`
   - Settings → User Management에 본인 Spotify 이메일 등록, Premium 계정 필요
   - Settings의 Client ID(32자리)를 채팅에 붙여 달라고 요청. 원하면 `python "<S>/spotify.py" setup --open`으로 Dashboard를 열어준다.
3. `Last.fm API key`가 FAIL이면 https://www.last.fm/api/account/create 에서 발급 안내.
   이 키는 비밀값이다: 채팅에 붙이면 대화 기록에 남는다고 알리고, 원하면 사용자가 직접 터미널에서
   `! python "<S>/spotify.py" setup` (대화형, 키 입력 숨김)을 실행하게 한다.
4. 받은 값으로 `python "<S>/spotify.py" setup --client-id <id> [--lastfm-key <key>]` 실행. 포트 FAIL이면 다른 포트를 Dashboard에 등록하게 하고 `--port <번호>` 추가.
5. `Spotify 로그인` FAIL → `python "<S>/spotify.py" login` 실행 (사용자가 브라우저에서 승인, 최대 5분 대기).
6. 다시 `doctor`. 403이면 User Management/Premium을, 다른 FAIL은 출력된 → 안내를 따른다.

값은 `~/.spotify-curator/config.json`에 저장되며 환경변수가 있으면 환경변수가 우선한다. 키 값을 응답에 다시 출력하지 않는다.
