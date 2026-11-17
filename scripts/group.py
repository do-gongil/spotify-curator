"""Group tracks into macro genres and order them so similar tracks sit together.

Usage:
    python group.py <tracks.json> <tags.json> [--out result.json]

tracks.json: [{"uri", "name", "artists": [..]}, ...]  (from spotify.py items)
tags.json:   {"artist name lowercase": ["tag", ...]}    (from tags.py)
Prints a compact summary; full result (groups with uris, mix order) goes to --out.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# ponytail: hand-written keyword map, first match wins. Edit here when a genre lands in the
# wrong bucket; switch to embedding similarity only if this map stops being enough.
EXACT = {
    "jazz hop": "hip-hop",
    "trip-hop": "electronic",
    "lofi": "lo-fi",
    "lo-fi": "lo-fi",
    "city pop": "j-pop",
}
# Macro names are used as `--key groups.<macro>` on the shell: keep them free of & . and spaces.
SUBSTR = [
    ("k-pop", "k-pop"), ("kpop", "k-pop"),
    ("j-pop", "j-pop"), ("jpop", "j-pop"), ("anime", "j-pop"),
    ("hip hop", "hip-hop"), ("hip-hop", "hip-hop"), ("hiphop", "hip-hop"),
    ("rap", "hip-hop"), ("trap", "hip-hop"),
    ("lo-fi", "lo-fi"),
    ("jazz", "jazz"),
    ("r&b", "rnb"), ("rnb", "rnb"), ("soul", "rnb"), ("funk", "rnb"),
    ("house", "electronic"), ("techno", "electronic"), ("edm", "electronic"),
    ("electro", "electronic"), ("trance", "electronic"), ("dubstep", "electronic"),
    ("drum and bass", "electronic"), ("synthwave", "electronic"),
    ("ambient", "ambient"),
    ("classical", "classical"), ("orchestra", "classical"),
    ("soundtrack", "soundtrack"),
    ("metal", "metal"),
    ("punk", "rock"), ("rock", "rock"), ("grunge", "rock"),
    ("indie", "indie"),
    ("folk", "folk"), ("acoustic", "folk"), ("singer-songwriter", "folk"),
    ("country", "country"),
    ("blues", "blues"),
    ("reggae", "latin"), ("latin", "latin"),
    ("ballad", "ballad"),
    ("pop", "pop"),
]
# Region-only tags: used only when no genre tag maps, so "korean, indie" -> indie.
REGIONAL = [("korean", "korean"), ("japanese", "j-pop")]
UNCLASSIFIED = "unclassified"


def artist_key(name):
    return name.strip().lower()


def primary_tags(track, tags):
    artists = track.get("artists") or [""]
    return [x.lower() for x in tags.get(artist_key(artists[0]), [])]


def _map_genre(tag):
    tag = tag.strip().lower()
    if tag in EXACT:
        return EXACT[tag]
    for keyword, macro in SUBSTR:
        if keyword in tag:
            return macro
    return None


def macro_of(tag_list):
    # Last.fm merges same-name artists (e.g. "Crush" also gets a metal band's tags). A Korean
    # sub-genre tag (k-rnb, k-indie, k-hiphop...) only lands on the Korean artist, so it wins.
    # k-pop is excluded: it is too broad to override a real genre like rnb.
    # ponytail: Korean-only heuristic; other regions' collisions still need `tags.py --set`.
    for tag in tag_list:
        tag = tag.strip().lower()
        if tag.startswith("k-") and tag not in ("k-pop", "k-pop idol"):
            macro = _map_genre(tag[2:])
            if macro:
                return macro
    for tag in tag_list:
        macro = _map_genre(tag)
        if macro:
            return macro
    for tag in tag_list:
        for keyword, macro in REGIONAL:
            if keyword in tag.lower():
                return macro
    return UNCLASSIFIED


def group_tracks(tracks, tags):
    groups = {}
    for track in tracks:
        macro = macro_of(primary_tags(track, tags))
        groups[macro] = groups.get(macro, []) + [track]
    return groups


def _features(track, tags):
    artists = track.get("artists") or [""]
    return set(primary_tags(track, tags)[:5]) | {"artist:" + artist_key(artists[0])}


def _jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0


def order_by_similarity(tracks, tags):
    # ponytail: greedy nearest neighbour, O(n^2); fine up to a few thousand tracks.
    if not tracks:
        return []
    feats = [_features(t, tags) for t in tracks]
    remaining = list(range(1, len(tracks)))
    order = [0]
    while remaining:
        last = feats[order[-1]]
        best = max(remaining, key=lambda i: (_jaccard(last, feats[i]), -i))
        order.append(best)
        remaining.remove(best)
    return [tracks[i] for i in order]


def mix_order(groups, tags):
    names = sorted(groups, key=lambda g: (g == UNCLASSIFIED, -len(groups[g]), g))
    return [t for g in names for t in order_by_similarity(groups[g], tags)]


def find_duplicates(tracks):
    seen = {}
    for track in tracks:
        artists = track.get("artists") or [""]
        key = (track.get("name", "").strip().lower(), artist_key(artists[0]))
        seen[key] = seen.get(key, []) + [track.get("uri")]
    return [
        {"name": k[0], "artist": k[1], "count": len(v), "uris": v}
        for k, v in seen.items()
        if len(v) > 1
    ]


def summarize(tracks, tags):
    groups = group_tracks(tracks, tags)
    genre_counts = sorted(((g, len(v)) for g, v in groups.items()), key=lambda x: (-x[1], x[0]))
    artists = Counter((t.get("artists") or ["?"])[0] for t in tracks)
    unclassified = sorted({(t.get("artists") or ["?"])[0] for t in groups.get(UNCLASSIFIED, [])})
    return {
        "total": len(tracks),
        "genres": [{"genre": g, "count": c} for g, c in genre_counts],
        "top_artists": [{"artist": a, "count": c} for a, c in artists.most_common(10)],
        "duplicates": find_duplicates(tracks),
        "unclassified_artists": unclassified,
        "groups": {g: [t["uri"] for t in order_by_similarity(v, tags)] for g, v in groups.items()},
        "mix_order": [t["uri"] for t in mix_order(groups, tags)],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("tracks")
    p.add_argument("tags")
    p.add_argument("--out", default="group_result.json")
    a = p.parse_args(argv)
    tracks = json.loads(Path(a.tracks).expanduser().read_text(encoding="utf-8-sig"))
    tags = json.loads(Path(a.tags).expanduser().read_text(encoding="utf-8-sig"))
    result = summarize(tracks, tags)
    a.out = Path(a.out).expanduser()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    compact = {k: result[k] for k in ("total", "genres", "top_artists", "unclassified_artists")}
    compact["duplicate_count"] = len(result["duplicates"])
    compact["out"] = str(Path(a.out).resolve())
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    print(json.dumps(compact, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
