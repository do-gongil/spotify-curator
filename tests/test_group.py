import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from group import macro_of, group_tracks, order_by_similarity, find_duplicates, summarize  # noqa: E402
import group  # noqa: E402


def t(uri, name, artist):
    return {"uri": uri, "name": name, "artists": [artist]}


TAGS = {
    "nujabes": ["jazz hop", "hip-hop", "instrumental"],
    "drake": ["hip-hop", "rap", "rnb"],
    "bill evans": ["jazz", "piano", "cool jazz"],
    "daft punk": ["electronic", "house", "french touch"],
    "iu": ["k-pop", "kpop", "female vocalists"],
    "unknown band": [],
}


def test_macro_of_uses_highest_ranked_mappable_tag():
    assert macro_of(["seen live", "jazz hop", "hip-hop"]) == "hip-hop"
    assert macro_of(["jazz", "piano"]) == "jazz"
    assert macro_of(["k-pop"]) == "k-pop"


def test_region_tag_only_used_when_no_genre_maps():
    assert macro_of(["korean", "indie"]) == "indie"
    assert macro_of(["korean", "hip-hop"]) == "hip-hop"
    assert macro_of(["korean", "seen live"]) == "korean"
    assert macro_of(["r&b"]) == "rnb"


def test_korean_subgenre_tag_beats_name_collision():
    # Last.fm merges same-name artists: "Dept" carries a rock band's tags plus k-rnb
    assert macro_of(["catala", "rock", "korean", "thai", "k-rnb"]) == "rnb"
    assert macro_of(["korean", "k-pop", "hip-hop", "rnb", "k-hiphop"]) == "hip-hop"
    assert macro_of(["k-indie", "korean", "indie pop"]) == "indie"
    # k-pop is too broad to override a real genre
    assert macro_of(["rnb", "k-pop", "soul"]) == "rnb"


def test_macro_names_are_shell_safe():
    import group
    for macro in {m for _, m in group.SUBSTR} | set(group.EXACT.values()) | {m for _, m in group.REGIONAL}:
        assert all(c not in macro for c in "&. ;|$"), macro


def test_macro_of_unclassified_when_no_tag_maps():
    assert macro_of([]) == "unclassified"
    assert macro_of(["seen live", "favorites"]) == "unclassified"


def test_group_tracks_by_primary_artist():
    tracks = [
        t("u1", "Aruarian Dance", "Nujabes"),
        t("u2", "Hotline Bling", "Drake"),
        t("u3", "Waltz for Debby", "Bill Evans"),
        t("u4", "Mystery", "Unknown Band"),
    ]
    groups = group_tracks(tracks, TAGS)
    assert [x["uri"] for x in groups["hip-hop"]] == ["u1", "u2"]
    assert [x["uri"] for x in groups["jazz"]] == ["u3"]
    assert [x["uri"] for x in groups["unclassified"]] == ["u4"]


def test_group_tracks_does_not_mutate_input():
    tracks = [t("u1", "A", "Drake")]
    before = [dict(x) for x in tracks]
    group_tracks(tracks, TAGS)
    assert tracks == before


def test_order_by_similarity_puts_similar_tracks_adjacent():
    tracks = [
        t("u1", "a", "Drake"),
        t("u2", "b", "Bill Evans"),
        t("u3", "c", "Nujabes"),
        t("u4", "d", "Daft Punk"),
    ]
    ordered = [x["uri"] for x in order_by_similarity(tracks, TAGS)]
    assert ordered[0] == "u1"
    assert ordered[1] == "u3"  # nujabes shares hip-hop with drake
    assert sorted(ordered) == ["u1", "u2", "u3", "u4"]


def test_order_by_similarity_empty():
    assert order_by_similarity([], TAGS) == []


def test_find_duplicates_by_uri_and_by_name_artist():
    tracks = [
        t("u1", "Song", "Drake"),
        t("u1", "Song", "Drake"),
        t("u9", "song ", "drake"),
        t("u2", "Other", "Drake"),
    ]
    dups = find_duplicates(tracks)
    assert len(dups) == 1
    assert dups[0]["count"] == 3


def test_summarize_counts_and_top_artists():
    tracks = [t("u1", "a", "Drake"), t("u2", "b", "Drake"), t("u3", "c", "Bill Evans")]
    s = summarize(tracks, TAGS)
    assert s["total"] == 3
    assert s["genres"] == [{"genre": "hip-hop", "count": 2}, {"genre": "jazz", "count": 1}]
    assert s["top_artists"][0] == {"artist": "Drake", "count": 2}
    assert s["mix_order"][:2] == ["u1", "u2"]


def test_ambiguity_flags_same_name_collision_only():
    assert group.ambiguity(["heavy metal", "k-rnb", "rnb"]) == {"korean": "rnb", "other": "metal"} or \
        group.ambiguity(["heavy metal", "k-rnb", "rnb"])["korean"] != group.ambiguity(["heavy metal", "k-rnb"])["other"]
    assert group.ambiguity(["k-rnb", "rnb", "soul"]) is None   # agree
    assert group.ambiguity(["k-rnb", "heavy metal"]) is None    # Korean tag ranks first
    assert group.ambiguity(["singer-songwriter", "k-indie"]) is None  # adjacent genres
    assert group.ambiguity(["k-pop", "dance"]) is None          # k-pop never counts
    assert group.ambiguity(["indie", "rock"]) is None           # no Korean tag


def test_summarize_reports_ambiguous_artists():
    tracks = [{"uri": "u1", "name": "Beautiful", "artists": ["Crush"]}]
    res = group.summarize(tracks, {"crush": ["heavy metal", "k-rnb"]})
    assert [a["artist"] for a in res["ambiguous_artists"]] == ["Crush"]
