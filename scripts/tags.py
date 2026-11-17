"""Artist -> genre tags for the primary artist of each track (Last.fm, fallback Spotify genres).

Usage:
    python tags.py <tracks.json> [--out tags.json]
    python tags.py --set "Artist=tag1,tag2" [--set ...]   # manual override (e.g. for unclassified)
Cache: ~/.spotify-curator/tags_cache.json (manual overrides win and are never refetched).
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spotify  # noqa: E402

CACHE = spotify.HOME / "tags_cache.json"
LASTFM = "https://ws.audioscrobbler.com/2.0/"
JUNK = {"seen live", "favorites", "favourites", "favorite", "favourite", "love", "awesome",
        "beautiful", "albums i own", "under 2000 listeners", "spotify", "my favorite", "cool"}
MIN_COUNT = 10
MAX_TAGS = 8


def clean_tags(raw, artist=""):
    a = artist.strip().lower()
    out = []
    for t in raw:
        name = t.get("name", "").strip().lower()
        if not name or name in JUNK or name == a or int(t.get("count", 0)) < MIN_COUNT or name in out:
            continue
        out.append(name)
    return out[:MAX_TAGS]


def lastfm_tags(artist, key):
    url = LASTFM + "?" + urllib.parse.urlencode({
        "method": "artist.gettoptags", "artist": artist, "api_key": key,
        "format": "json", "autocorrect": 1})
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.load(r)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        # never print the URL: it contains the api key
        print(f"WARN: Last.fm 조회 실패 ({artist}): {getattr(e, 'code', '') or type(e).__name__}", file=sys.stderr)
        return []
    if "error" in data:  # e.g. invalid key (10) or artist not found (6)
        if data["error"] == 10:
            print("ERROR: LASTFM_API_KEY가 유효하지 않습니다.", file=sys.stderr)
        return []
    return clean_tags(data.get("toptags", {}).get("tag", []), artist)


def load_cache():
    return json.loads(CACHE.read_text(encoding="utf-8-sig")) if CACHE.exists() else {}


def save_cache(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("tracks", nargs="?")
    p.add_argument("--out")
    p.add_argument("--set", action="append", default=[], help='"Artist=tag1,tag2"')
    a = p.parse_args(argv)
    cache = load_cache()

    for item in a.set:
        artist, _, tags = item.partition("=")
        cache[artist.strip().lower()] = {"tags": [x.strip().lower() for x in tags.split(",") if x.strip()], "manual": True}
    if a.set:
        save_cache(cache)
        print(f"수동 태그 {len(a.set)}개 저장")
        if not a.tracks:
            return

    if not a.tracks:
        p.error("tracks.json 또는 --set 이 필요합니다")
    tracks = json.loads(Path(a.tracks).expanduser().read_text(encoding="utf-8-sig"))
    artists = {}
    for t in tracks:
        if t.get("artists"):
            artists.setdefault(t["artists"][0].strip().lower(), (t["artists"][0], (t.get("artist_ids") or [None])[0]))

    key = os.environ.get("LASTFM_API_KEY")
    if not key:
        print("WARN: LASTFM_API_KEY 없음 — Spotify genres만 사용합니다 (정확도 낮음).", file=sys.stderr)
    stats = {"cache": 0, "lastfm": 0, "spotify": 0, "empty": 0}
    for i, (k, (name, aid)) in enumerate(artists.items()):
        if k in cache and (cache[k]["tags"] or cache[k].get("manual")):  # empty results get retried
            stats["cache"] += 1
            continue
        tags, src = [], "empty"
        if key:
            tags = lastfm_tags(name, key)
            src = "lastfm" if tags else src
            time.sleep(0.2)  # Last.fm asks for <= 5 req/s
        if not tags and aid:
            try:
                tags = [g.lower() for g in spotify.artist_genres(aid)][:MAX_TAGS]
                src = "spotify" if tags else src
            except urllib.error.HTTPError:
                pass
        cache[k] = {"tags": tags}
        stats[src] += 1
        if i % 25 == 24:
            save_cache(cache)
    save_cache(cache)

    result = {k: cache[k]["tags"] for k in artists}
    out = spotify.out_path(a.out, spotify.WORK / "tags.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"아티스트 {len(artists)}명: {stats} → {out.resolve()}")


if __name__ == "__main__":
    main()
