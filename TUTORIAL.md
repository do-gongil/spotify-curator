# 튜토리얼

[English](TUTORIAL.en.md) · 한국어 · [README](README.md)

처음 설치부터 첫 플레이리스트를 만들기까지 10분 정도 걸립니다.

## 0. 준비물
- Spotify **Premium** 계정
- Claude Code
- Python 3.7+ (`python --version` 또는 `python3 --version`으로 확인)

## 1. 플러그인 설치
Claude Code에서:
```
/plugin marketplace add do-gongil/spotify-curator
/plugin install spotify-curator@spotify-curator
```

## 2. 설정 (Claude에게 맡기기)
Claude Code에 이렇게 말합니다.
```
spotify-curator 설정해줘
```
Claude가 `setup` 스킬로 아래 과정을 안내합니다. 직접 해야 하는 것은 웹사이트 두 곳에서 키를 받는 일뿐입니다.

### 2-1. Spotify 앱 만들기 (사용자가 직접)
1. https://developer.spotify.com/dashboard 에 로그인 → **Create app**
2. App name·description은 아무거나, **Redirect URI**에 `http://127.0.0.1:8888/callback` 입력 후 Add
3. **Which API/SDKs**에서 *Web API* 체크 → 약관 동의 → Save
4. 앱 → **Settings** → **User Management**에 본인 Spotify 계정 이메일 추가 (안 하면 403 오류)
5. Settings의 **Client ID**(32자리)를 복사해 Claude에게 붙여 넣기

> Client ID는 비밀값이 아닙니다. Client secret은 필요 없습니다.

### 2-2. Last.fm API 키 받기 (사용자가 직접)
1. https://www.last.fm/api/account/create (Last.fm 계정 필요)
2. Application name만 적고 제출 → **API key** 복사
3. 이 키는 비밀값입니다. 채팅에 붙이면 대화 기록에 남습니다. 싫다면 Claude Code 입력창에서 직접 실행하세요:
   ```
   ! python "<플러그인 경로>/scripts/spotify.py" setup
   ```
   (입력이 화면에 보이지 않습니다. 경로는 Claude가 알려줍니다.)

### 2-3. 로그인과 점검 (Claude가 실행)
- Claude가 `spotify.py login`을 실행하면 브라우저가 열립니다 → **동의** 클릭
- 이어서 `spotify.py doctor`가 모든 항목을 점검합니다:
  ```
  [OK]   Spotify Client ID
  [OK]   Last.fm API key
  [OK]   Spotify 로그인 (이름)
  [OK]   Spotify API 접근
  준비 완료
  ```

설정값은 `~/.spotify-curator/config.json`에 저장되므로 환경변수 설정이나 터미널 재시작이 필요 없습니다.

## 3. 써보기

| 하고 싶은 것 | 이렇게 말하기 |
|---|---|
| 설명으로 새 플레이리스트 | "DPR IAN 같은 노스탤지어 무드 플레이리스트 25곡 만들어줘" |
| 내 플레이리스트에서 장르 골라 모으기 | "플레이리스트 A, B에서 R&B만 모아서 새로 만들어줘" |
| 분석 | "내 좋아요 곡 장르 분포랑 중복곡 알려줘" |
| 장르별로 나누기 / 재정렬 | "이 플레이리스트 장르별로 나눠줘", "비슷한 곡끼리 이어지게 순서 정리해줘" |
| 비슷한 곡 추가 | "Faded Polaroids에 비슷한 곡 10개 더 넣어줘" |

Claude는 항상 곡 목록을 먼저 보여주고 확인을 받은 뒤 Spotify에 반영합니다. 순서를 바꾸기 전에는 자동으로 백업합니다.

## 4. 문제 해결
"spotify-curator 점검해줘"라고 말하면 Claude가 `doctor`를 실행해 원인을 알려줍니다.

| 증상 | 원인 / 해결 |
|---|---|
| 403 오류 | User Management에 이메일 미등록, 또는 Premium이 아님 |
| `INVALID_CLIENT: Invalid redirect URI` | Dashboard의 Redirect URI가 `http://127.0.0.1:8888/callback`과 정확히 같은지 확인 (`localhost` 불가) |
| 로그인 포트 사용 중 | Dashboard에 다른 포트(예: 8899)로 Redirect URI 추가 후 `setup --port 8899` |
| 토큰 만료 | 최초 승인 후 6개월. `spotify.py login` 다시 실행 |
| 장르가 이상하게 분류됨 | Last.fm 태그 문제. "Crush는 k-rnb로 지정해줘"처럼 말하면 수동 지정 |
| 팔로우한 플레이리스트가 안 읽힘 | Spotify API 제한. 본인 소유/공동 플레이리스트만 가능 |

## 5. 로그아웃 / 삭제
- `~/.spotify-curator/` 폴더 삭제 (토큰·설정·캐시·백업)
- Spotify 계정 설정 → **Apps**에서 앱 접근 해제
- `/plugin uninstall spotify-curator`
