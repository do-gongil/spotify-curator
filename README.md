# spotify-curator

[English](README.en.md) · 한국어

Claude Code 플러그인. Spotify 플레이리스트를 장르별로 선별·생성·믹스·분석·확장한다.

| 스킬 | 하는 일 | 예시 프롬프트 |
|---|---|---|
| `genre-curate` | 지정한 플레이리스트들(또는 좋아요 곡)에서 비슷한 장르만 모아 새 플레이리스트 | "내 플레이리스트 A, B에서 재즈만 모아줘" |
| `playlist-from-prompt` | 짧은 설명 → Claude가 후보 선정 → Spotify 검색으로 실존 검증 → 생성 | "비 오는 밤 운전용 시티팝 25곡 만들어줘" |
| `playlist-mix` | 한 플레이리스트를 유사 그룹별 하위 플레이리스트로 분할 + 원본을 비슷한 곡끼리 재정렬(자동 백업) | "이 플레이리스트 장르별로 나눠줘" |
| `playlist-report` | 장르 분포, 아티스트 편중, 중복곡 요약 (읽기 전용) | "내 좋아요 곡 분석해줘" |
| `playlist-extend` | 플레이리스트 분위기에 맞는 곡 N개 추천·검증 후 추가 | "이 플레이리스트에 비슷한 곡 10개 더 넣어줘" |

## 요구사항
- Python 3.7+ (표준 라이브러리만 사용, 설치할 패키지 없음. `pytest`는 테스트에만 필요). macOS/Linux에서 `python`이 없으면 `python3`
- Spotify **Premium** 계정 (2026-02 이후 Dev Mode 정책)
- Claude Code

## 설정 (1회)

1. **Spotify 앱**
   - https://developer.spotify.com/dashboard → Create app → API: *Web API*
   - Redirect URI: `http://127.0.0.1:8888/callback` (`localhost`는 허용되지 않음).
     8888은 Jupyter 기본 포트라 겹치면 다른 포트로 등록하고 `SPOTIFY_REDIRECT_PORT`를 같은 값으로 설정
   - 앱 설정의 **User Management**에 본인 Spotify 계정 이메일 등록 (안 하면 403)
   - Client ID를 환경변수 `SPOTIFY_CLIENT_ID`로 설정 (PKCE라 client secret 불필요)
2. **Last.fm API 키** (장르 태그용, 무료): https://www.last.fm/api/account/create → `LASTFM_API_KEY`
3. 환경변수 설정 후 **터미널/Claude Code를 재시작**해야 반영된다.

   Windows (PowerShell):
   ```powershell
   [Environment]::SetEnvironmentVariable("SPOTIFY_CLIENT_ID", "<client id>", "User")
   [Environment]::SetEnvironmentVariable("LASTFM_API_KEY", "<key>", "User")
   ```
   macOS / Linux (`~/.zshrc` 또는 `~/.bashrc`):
   ```sh
   export SPOTIFY_CLIENT_ID="<client id>"
   export LASTFM_API_KEY="<key>"
   ```
4. 로그인: `python scripts/spotify.py login` (브라우저 승인). refresh token은 최초 승인 후 6개월에 만료되므로 그때 다시 로그인.

## 설치

Claude Code에서:
```
/plugin marketplace add do-gongil/spotify-curator
/plugin install spotify-curator@spotify-curator
```
스킬 실행 중 로그인이 필요하면 Claude가 실행할 명령을 알려준다.
개발 중에는 저장소를 클론해서 `claude --plugin-dir <클론 경로>`.

## 데이터와 보안
- 데이터 위치: `~/.spotify-curator/` (`token.json`, `tags_cache.json`, `work/`, `backups/`). `SPOTIFY_CURATOR_HOME`으로 변경 가능
- `token.json`은 **평문**으로 저장된다 (POSIX에선 0600). 공유 폴더에 두지 말 것
- 로그아웃: `token.json` 삭제 후 Spotify 계정 설정 → Apps에서 앱 접근 해제
- 새로 만드는 플레이리스트는 비공개. 삭제 기능은 없음. 재정렬 전에는 자동 백업

## 구조
- `scripts/spotify.py` — 의존성 없는 Web API CLI (`python scripts/spotify.py -h`)
- `scripts/tags.py` — 아티스트 → 장르 태그 (Last.fm, 없으면 Spotify genres), `~/.spotify-curator/tags_cache.json` 캐시
- `scripts/group.py` — 태그 → 메인 장르 매핑, 그룹핑, 유사도 순 정렬. 매핑이 틀리면 `EXACT`/`SUBSTR` 표를 수정

## 제약 (Spotify Web API, 신규 Dev Mode 앱)
- 플레이리스트 **폴더**는 API로 읽을 수 없음 → 플레이리스트 이름으로 지정
- 곡 목록은 **본인 소유/공동** 플레이리스트만 읽힘 (팔로우만 한 플레이리스트, Spotify 알고리즘 플레이리스트 불가)
- audio-features / recommendations / related-artists 사용 불가 → 유사도는 장르 태그 기반, 추천은 Claude + 검색 검증
- Spotify artist genres는 Dev Mode에서 비어 있음 → 사실상 Last.fm 태그에 의존. Last.fm은 동명 아티스트 태그가 섞임
  (예: Crush에 heavy metal). `k-rnb`·`k-indie` 같은 한국 세부 장르 태그가 있으면 자동 우선하고, 그 외는
  `python scripts/tags.py --set "Artist=genre1,genre2"`로 수동 지정
- Dev Mode는 개인·비상업 용도, 앱당 사용자 5명
- 플레이리스트 삭제(언팔로우) 엔드포인트가 2026-02에 바뀌어 이 도구는 삭제를 지원하지 않음 → Spotify 앱에서 삭제
- `replace`(재정렬)는 곡별 '추가한 날짜'를 초기화함. 로컬 파일/에피소드가 섞인 플레이리스트는 거부
- Developer Terms의 AI 관련 조항(모델 학습 금지): 이 도구는 개인 큐레이션용이며 데이터를 학습에 쓰지 않음

## 테스트
```
python -m pytest tests -q
```

## 라이선스
MIT
