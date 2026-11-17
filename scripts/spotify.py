"""Minimal Spotify Web API CLI (stdlib only) for the spotify-curator plugin.

Commands (outputs land in ~/.spotify-curator/work unless --out is given):
  login                                   PKCE login in the browser (needs SPOTIFY_CLIENT_ID)
  playlists                               list your playlists (readable = you own / collaborate)
  items <playlist>... [--out f]           tracks of playlists (name, unique substring, id, or "liked")
  search <"Artist - Title">... [--file f] best match per query with confidence
  create <name> <uris.json> [--key k] [--description d]
  add <playlist> <uris.json> [--key k]
  replace <playlist> <uris.json> [--key k] (auto backup first)
  backup <playlist>
uris.json: list of uris or {"uri":..} objects; --key picks a dotted path, e.g. groups.hip-hop
"""
import argparse
import base64
import difflib
import hashlib
import http.server
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

HOME = Path(os.environ.get("SPOTIFY_CURATOR_HOME", Path.home() / ".spotify-curator"))
WORK = HOME / "work"
TOKEN_FILE = HOME / "token.json"
API = "https://api.spotify.com/v1"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
PORT = int(os.environ.get("SPOTIFY_REDIRECT_PORT", "8888"))
REDIRECT_URI = f"http://127.0.0.1:{PORT}/callback"
SCOPES = " ".join([
    "playlist-read-private", "playlist-read-collaborative",
    "playlist-modify-private", "playlist-modify-public",
    "user-library-read", "user-read-recently-played", "user-top-read",
])


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def client_id():
    cid = os.environ.get("SPOTIFY_CLIENT_ID")
    if not cid:
        die("SPOTIFY_CLIENT_ID 환경변수가 없습니다. README의 설정 단계를 참고하세요.")
    return cid


# ---------- pure helpers (unit-tested) ----------

def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def track_from_entry(entry, playlist_name):
    # Feb 2026 renamed playlist entry field "track" -> "item"; accept both.
    t = entry.get("item") or entry.get("track")
    if not t or t.get("type", "track") != "track" or t.get("is_local") or not t.get("uri", "").startswith("spotify:track:"):
        return None
    return {
        "uri": t["uri"],
        "name": t.get("name", ""),
        "artists": [a.get("name", "") for a in t.get("artists", [])],
        "artist_ids": [a.get("id") for a in t.get("artists", []) if a.get("id")],
        "added_at": entry.get("added_at"),
        "playlist": playlist_name,
    }


def resolve_playlist(query, playlists, exact=False):
    q = query.strip().casefold()
    exact_hits = [p for p in playlists if p["id"] == query.strip() or p["name"].casefold() == q]
    if len(exact_hits) == 1:
        return exact_hits[0]
    if len(exact_hits) > 1:
        die(f"'{query}' 이름의 플레이리스트가 {len(exact_hits)}개입니다. id로 지정하세요: "
            + ", ".join(p["id"] for p in exact_hits))
    if exact:
        die(f"'{query}'와 정확히 일치하는 플레이리스트가 없습니다 (수정/삭제는 정확한 이름 또는 id 필요).")
    hits = [p for p in playlists if q in p["name"].casefold()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        die(f"플레이리스트 '{query}'를 찾을 수 없습니다. `playlists`로 목록을 확인하세요.")
    die(f"'{query}'가 여러 플레이리스트와 일치합니다: " + ", ".join(p["name"] for p in hits[:10]))


def out_path(path, default):
    p = Path(path).expanduser() if path else default
    if p.resolve() == TOKEN_FILE.resolve():
        die("--out이 토큰 파일을 가리킵니다.")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_uris(path, key=None):
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8-sig"))
    for part in (key.split(".") if key else []):
        if not isinstance(data, dict) or part not in data:
            die(f"{path}에 키 '{key}'가 없습니다.")
        data = data[part]
    if not isinstance(data, list):
        die(f"{path}{'의 ' + key if key else ''}가 리스트가 아닙니다.")
    uris = [x["uri"] if isinstance(x, dict) else x for x in data]
    bad = [u for u in uris if not (isinstance(u, str) and u.startswith("spotify:track:"))]
    if bad:
        die(f"track uri가 아닌 값이 있습니다: {bad[:3]}")
    return uris


def _norm(s):
    s = s.casefold()
    s = re.sub(r"\s+-\s+.*(remaster|version|edit|mix|live|mono|stereo).*$", "", s)
    s = re.sub(r"\((?:[^)]*(remaster|version|edit|feat|with)[^)]*)\)", "", s)
    return re.sub(r"\s+", " ", s).strip()


def match_confidence(artist, title, track):
    t_score = difflib.SequenceMatcher(None, _norm(title), _norm(track.get("name", ""))).ratio()
    if not artist:
        return round(t_score, 3)
    names = [a.get("name", "") for a in track.get("artists", [])] or [""]
    a_score = max(difflib.SequenceMatcher(None, artist.casefold(), n.casefold()).ratio() for n in names)
    return round(0.6 * t_score + 0.4 * a_score, 3)


def parse_query(line):
    if " - " in line:
        artist, title = line.split(" - ", 1)
        return artist.strip(), title.strip()
    return "", line.strip()


# ---------- auth ----------

def _post_token(form):
    req = urllib.request.Request(TOKEN_URL, data=urllib.parse.urlencode(form).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if "invalid_grant" in body:
            die(f"토큰이 만료/취소되었습니다 (refresh token은 최초 승인 후 6개월). `python \"{Path(__file__).resolve()}\" login`을 다시 실행하세요.")
        try:
            err = json.loads(body)
            body = f"{err.get('error')}: {err.get('error_description', '')}"
        except json.JSONDecodeError:
            body = body[:200]
        die(f"토큰 요청 실패 {e.code}: {body}")
    tok["expires_at"] = int(time.time()) + int(tok.get("expires_in", 3600)) - 60
    return tok


def _save_token(tok):
    HOME.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = TOKEN_FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(tok, f)
    os.replace(tmp, TOKEN_FILE)


def login():
    cid = client_id()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": cid, "response_type": "code", "redirect_uri": REDIRECT_URI,
        "scope": SCOPES, "code_challenge_method": "S256", "code_challenge": challenge, "state": state,
    })
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
            if u.path != "/callback" or not secrets.compare_digest(qs.get("state", ""), state):
                self.send_response(404)  # ignore stray requests (favicon, scans)
                self.end_headers()
                return
            result.update(qs)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("인증 완료. 이 창을 닫아도 됩니다.".encode())

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"브라우저에서 Spotify 로그인을 진행하세요. 열리지 않으면 이 URL을 여세요:\n{url}")
    webbrowser.open(url)
    deadline = time.time() + 300
    server.timeout = 5
    while not result and time.time() < deadline:
        server.handle_request()
    server.server_close()
    if "code" not in result:
        die(f"로그인 실패: {result.get('error', '응답 없음(시간 초과)')}")
    tok = _post_token({"grant_type": "authorization_code", "code": result["code"],
                       "redirect_uri": REDIRECT_URI, "client_id": cid, "code_verifier": verifier})
    _save_token(tok)
    me = api("GET", "/me")
    print(f"로그인 완료: {me.get('display_name') or me.get('id')}")


def access_token(force_refresh=False):
    if not TOKEN_FILE.exists():
        die(f"로그인이 필요합니다: python \"{Path(__file__).resolve()}\" login")
    tok = json.loads(TOKEN_FILE.read_text(encoding="utf-8-sig"))
    if force_refresh or time.time() >= tok.get("expires_at", 0):
        new = _post_token({"grant_type": "refresh_token", "refresh_token": tok["refresh_token"],
                           "client_id": client_id()})
        new.setdefault("refresh_token", tok["refresh_token"])
        _save_token(new)
        tok = new
    return tok["access_token"]


def api(method, path, params=None, body=None, _retry=True):
    url = path if path.startswith("http") else API + path
    if not url.startswith(API + "/"):
        die(f"Spotify API 외부 URL로 토큰을 보내지 않습니다: {urllib.parse.urlparse(url).netloc}")
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {access_token()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        if e.code == 429 and _retry:
            time.sleep(int(e.headers.get("Retry-After", "2")) + 1)
            return api(method, path, params, body, _retry=False)
        if e.code == 401 and _retry:
            access_token(force_refresh=True)
            return api(method, path, params, body, _retry=False)
        err = urllib.error.HTTPError(e.url, e.code, e.read().decode(errors="replace"), e.headers, None)
        raise err from None


def api_items(method, playlist_id, params=None, body=None):
    """Playlist items endpoint; falls back to the pre-2026 /tracks path on 404."""
    try:
        return api(method, f"/playlists/{playlist_id}/items", params, body)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        return api(method, f"/playlists/{playlist_id}/tracks", params, body)


def paged(path, params):
    page = api("GET", path, params)
    while True:
        yield from page.get("items", [])
        if not page.get("next"):
            return
        page = api("GET", page["next"])


# ---------- commands ----------

def fetch_playlists():
    me = api("GET", "/me")["id"]
    out = []
    for p in paged("/me/playlists", {"limit": 50}):
        if not p:
            continue
        counts = p.get("items") or p.get("tracks") or {}
        owner = (p.get("owner") or {}).get("id")
        out.append({"id": p["id"], "name": p["name"], "owner": owner,
                    "total": counts.get("total"),
                    "readable": owner == me or bool(p.get("collaborative"))})
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "playlists.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def cached_playlists():
    f = WORK / "playlists.json"
    return json.loads(f.read_text(encoding="utf-8-sig")) if f.exists() else fetch_playlists()


def find_playlist(query, exact=False):
    if exact:  # destructive commands: always fresh list, exact name or id only
        return resolve_playlist(query, fetch_playlists(), exact=True)
    try:
        return resolve_playlist(query, cached_playlists())
    except SystemExit:
        return resolve_playlist(query, fetch_playlists())  # cache may be stale


def cmd_playlists(a):
    for p in fetch_playlists():
        flag = "" if p["readable"] else "  (팔로우만 — 곡 조회 불가)"
        print(f"{p['total'] if p['total'] is not None else '?':>5}  {p['name']}  [{p['id']}]{flag}")


def read_playlist_entries(p):
    """Return (tracks, raw_entry_count). raw count includes local files/episodes we skip."""
    if not p.get("readable", True):
        die(f"'{p['name']}'는 본인 소유/공동 플레이리스트가 아니라 API로 곡을 읽을 수 없습니다.")
    out, raw, offset = [], 0, 0
    while True:
        page = api_items("GET", p["id"], {"limit": 50, "offset": offset})
        entries = page.get("items", [])
        raw += len(entries)
        out += [x for e in entries if (x := track_from_entry(e, p["name"]))]
        if not page.get("next"):
            return out, raw
        offset += 50


def read_tracks(query):
    if query.casefold() == "liked":
        return [x for e in paged("/me/tracks", {"limit": 50}) if (x := track_from_entry(e, "Liked Songs"))]
    return read_playlist_entries(find_playlist(query))[0]


def cmd_items(a):
    tracks = []
    for q in a.playlists:
        got = read_tracks(q)
        print(f"{q}: {len(got)}곡")
        tracks += got
    out = out_path(a.out, WORK / "tracks.json")
    out.write_text(json.dumps(tracks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"총 {len(tracks)}곡 → {out.resolve()}")


def search_one(line):
    artist, title = parse_query(line)
    q = f"track:{title} artist:{artist}" if artist else title
    items = api("GET", "/search", {"q": q, "type": "track", "limit": 5}).get("tracks", {}).get("items", [])
    if not items and artist:
        items = api("GET", "/search", {"q": f"{artist} {title}", "type": "track", "limit": 5}).get("tracks", {}).get("items", [])
    if not items:
        return {"query": line, "uri": None, "confidence": 0}
    best = max(items, key=lambda t: match_confidence(artist, title, t))
    return {"query": line, "uri": best["uri"], "name": best["name"],
            "artists": [x["name"] for x in best["artists"]],
            "confidence": match_confidence(artist, title, best)}


def cmd_search(a):
    lines = list(a.queries)
    if a.file:
        lines += [x.strip() for x in Path(a.file).expanduser().read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    results = [search_one(x) for x in lines]
    out = out_path(a.out, WORK / "search.json")
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in results:
        found = f"{', '.join(r.get('artists', []))} - {r.get('name')}" if r["uri"] else "(없음)"
        print(f"{r['confidence']:.2f}  {r['query']}  →  {found}")
    print(f"→ {out.resolve()}")


def add_uris(playlist_id, uris):
    for part in chunks(uris, 100):
        api_items("POST", playlist_id, body={"uris": part})


def cmd_create(a):
    uris = load_uris(a.uris, a.key)
    p = api("POST", "/me/playlists", body={"name": a.name, "description": a.description or "", "public": False})
    add_uris(p["id"], uris)
    fetch_playlists()
    print(f"생성: {a.name} ({len(uris)}곡) {p.get('external_urls', {}).get('spotify', p['id'])}")


def cmd_add(a):
    p = find_playlist(a.playlist)
    uris = load_uris(a.uris, a.key)
    add_uris(p["id"], uris)
    print(f"추가: {p['name']} +{len(uris)}곡")


def backup(p):
    tracks, raw = read_playlist_entries(p)
    uris = [t["uri"] for t in tracks]
    d = HOME / "backups"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{p['id']}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    f.write_text(json.dumps({"playlist_id": p["id"], "name": p["name"], "uris": uris,
                             "skipped_entries": raw - len(uris)}, ensure_ascii=False), encoding="utf-8")
    return f, uris, raw


def cmd_backup(a):
    f, uris, raw = backup(find_playlist(a.playlist))
    print(f"백업: {len(uris)}곡 → {f}" + (f" (로컬 파일/에피소드 {raw - len(uris)}개는 백업 불가)" if raw > len(uris) else ""))


def cmd_replace(a):
    p = find_playlist(a.playlist, exact=True)
    uris = load_uris(a.uris, a.key)
    f, old, raw = backup(p)
    if raw != len(old):
        die(f"이 플레이리스트에는 API로 다시 넣을 수 없는 항목(로컬 파일/에피소드) {raw - len(old)}개가 있어 "
            "replace하면 사라집니다. 중단합니다.")
    if sorted(old) != sorted(uris) and not a.allow_change:
        die(f"새 목록이 기존 곡 구성과 다릅니다 (기존 {len(old)}, 새 {len(uris)}). "
            "재정렬이 아니라 구성 변경이 의도라면 --allow-change를 붙이세요. 백업: " + str(f))
    restore = f'replace "{p["id"]}" "{f}" --key uris --allow-change'
    try:
        api_items("PUT", p["id"], body={"uris": uris[:100]})
        add_uris(p["id"], uris[100:])
    except (urllib.error.HTTPError, urllib.error.URLError):
        print(f"ERROR: 교체 도중 실패해 플레이리스트가 일부만 반영됐을 수 있습니다. 복원: {restore}", file=sys.stderr)
        raise
    print(f"교체: {p['name']} {len(uris)}곡 (백업 {f}; 되돌리기: {restore})")


# ponytail: no delete command; DELETE /playlists/{id}/followers was removed in Feb 2026
# (replacement DELETE /me/library is untested). Delete playlists in the Spotify app.


def artist_genres(artist_id):
    return api("GET", f"/artists/{artist_id}").get("genres", [])


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login").set_defaults(fn=lambda a: login())
    sub.add_parser("playlists").set_defaults(fn=cmd_playlists)
    s = sub.add_parser("items"); s.add_argument("playlists", nargs="+"); s.add_argument("--out"); s.set_defaults(fn=cmd_items)
    s = sub.add_parser("search"); s.add_argument("queries", nargs="*"); s.add_argument("--file"); s.add_argument("--out"); s.set_defaults(fn=cmd_search)
    s = sub.add_parser("create"); s.add_argument("name"); s.add_argument("uris"); s.add_argument("--key"); s.add_argument("--description"); s.set_defaults(fn=cmd_create)
    s = sub.add_parser("add"); s.add_argument("playlist"); s.add_argument("uris"); s.add_argument("--key"); s.set_defaults(fn=cmd_add)
    s = sub.add_parser("replace"); s.add_argument("playlist"); s.add_argument("uris"); s.add_argument("--key")
    s.add_argument("--allow-change", action="store_true"); s.set_defaults(fn=cmd_replace)
    s = sub.add_parser("backup"); s.add_argument("playlist"); s.set_defaults(fn=cmd_backup)
    a = p.parse_args(argv)
    try:
        a.fn(a)
    except urllib.error.HTTPError as e:
        hint = " (Dev Mode 앱 권한/소유권 문제일 수 있음)" if e.code == 403 else ""
        die(f"Spotify API {e.code}{hint}: {e.msg}")


if __name__ == "__main__":
    main()
