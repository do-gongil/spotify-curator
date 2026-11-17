import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import spotify  # noqa: E402
import tags as tagmod  # noqa: E402


def test_chunks_splits_by_100():
    uris = [f"spotify:track:{i}" for i in range(250)]
    parts = list(spotify.chunks(uris, 100))
    assert [len(p) for p in parts] == [100, 100, 50]
    assert sum(parts, []) == uris


def test_track_from_entry_accepts_new_item_field_and_old_track_field():
    new = {"added_at": "2026-01-01T00:00:00Z",
           "item": {"type": "track", "uri": "spotify:track:A", "name": "Song",
                    "artists": [{"name": "Art", "id": "aid"}], "is_local": False}}
    old = {"added_at": "x", "track": dict(new["item"], uri="spotify:track:B")}
    assert spotify.track_from_entry(new, "PL")["uri"] == "spotify:track:A"
    assert spotify.track_from_entry(new, "PL")["artists"] == ["Art"]
    assert spotify.track_from_entry(new, "PL")["artist_ids"] == ["aid"]
    assert spotify.track_from_entry(old, "PL")["uri"] == "spotify:track:B"


def test_track_from_entry_skips_episodes_local_and_missing():
    assert spotify.track_from_entry({"item": None}, "PL") is None
    assert spotify.track_from_entry({"item": {"type": "episode", "uri": "x"}}, "PL") is None
    assert spotify.track_from_entry(
        {"item": {"type": "track", "uri": "spotify:local:x", "is_local": True, "name": "n", "artists": []}}, "PL"
    ) is None


PLAYLISTS = [
    {"id": "1", "name": "Chill Jazz"},
    {"id": "2", "name": "chill hop"},
    {"id": "3", "name": "Workout"},
]


def test_resolve_playlist_exact_casefold_then_unique_substring():
    assert spotify.resolve_playlist("chill jazz", PLAYLISTS)["id"] == "1"
    assert spotify.resolve_playlist("work", PLAYLISTS)["id"] == "3"
    assert spotify.resolve_playlist("3", PLAYLISTS)["id"] == "3"


def test_resolve_playlist_ambiguous_or_missing_raises():
    with pytest.raises(SystemExit):
        spotify.resolve_playlist("chill", PLAYLISTS)
    with pytest.raises(SystemExit):
        spotify.resolve_playlist("nothing", PLAYLISTS)


def test_load_uris_list_objects_and_dotted_key(tmp_path):
    f = tmp_path / "u.json"
    f.write_text(json.dumps(["spotify:track:a", {"uri": "spotify:track:b"}]))
    assert spotify.load_uris(str(f)) == ["spotify:track:a", "spotify:track:b"]
    g = tmp_path / "g.json"
    g.write_text(json.dumps({"groups": {"hip-hop": ["spotify:track:c"]}, "mix_order": ["spotify:track:d"]}))
    assert spotify.load_uris(str(g), "groups.hip-hop") == ["spotify:track:c"]
    assert spotify.load_uris(str(g), "mix_order") == ["spotify:track:d"]


def test_load_uris_rejects_non_track_strings(tmp_path):
    f = tmp_path / "u.json"
    f.write_text(json.dumps(["not a uri"]))
    with pytest.raises(SystemExit):
        spotify.load_uris(str(f))


def test_match_confidence():
    hit = {"name": "Hotline Bling", "artists": [{"name": "Drake"}]}
    miss = {"name": "Hotline Bling (Cover)", "artists": [{"name": "Some Band"}]}
    assert spotify.match_confidence("Drake", "Hotline Bling", hit) > 0.9
    assert spotify.match_confidence("Drake", "Hotline Bling", miss) < 0.7


def test_parse_query_line():
    assert spotify.parse_query("Drake - Hotline Bling") == ("Drake", "Hotline Bling")
    assert spotify.parse_query("just a title") == ("", "just a title")


def test_resolve_playlist_exact_mode_rejects_substring_and_duplicates():
    with pytest.raises(SystemExit):
        spotify.resolve_playlist("work", PLAYLISTS, exact=True)
    dup = PLAYLISTS + [{"id": "4", "name": "Workout"}]
    with pytest.raises(SystemExit):
        spotify.resolve_playlist("Workout", dup)
    assert spotify.resolve_playlist("4", dup, exact=True)["id"] == "4"


# ---------- fake API for read/backup/replace ----------

def entry(uri, kind="track", local=False):
    return {"added_at": "2026-01-01T00:00:00Z",
            "item": {"type": kind, "uri": uri, "is_local": local, "name": uri, "artists": [{"name": "A", "id": "a"}]}}


class FakeAPI:
    def __init__(self, entries):
        self.entries = entries
        self.calls = []

    def __call__(self, method, playlist_id, params=None, body=None):
        self.calls.append((method, body and len(body["uris"])))
        if method == "GET":
            off, lim = params["offset"], params["limit"]
            page = self.entries[off:off + lim]
            return {"items": page, "next": "x" if off + lim < len(self.entries) else None}
        return {}


@pytest.fixture
def fake(monkeypatch, tmp_path):
    def make(entries):
        api = FakeAPI(entries)
        monkeypatch.setattr(spotify, "api_items", api)
        monkeypatch.setattr(spotify, "HOME", tmp_path)
        monkeypatch.setattr(spotify, "find_playlist", lambda q, exact=False: {"id": "P", "name": "PL"})
        return api
    return make


def replace_args(tmp_path, uris, allow=False):
    f = tmp_path / "new.json"
    f.write_text(json.dumps(uris))
    return type("A", (), {"playlist": "PL", "uris": str(f), "key": None, "allow_change": allow})()


def test_read_playlist_entries_paginates_and_counts_raw(fake):
    entries = [entry(f"spotify:track:{i}") for i in range(120)] + [entry("spotify:episode:e", kind="episode")]
    fake(entries)
    tracks, raw = spotify.read_playlist_entries({"id": "P", "name": "PL"})
    assert len(tracks) == 120 and raw == 121


def test_replace_reorders_with_put_100_then_post_rest_and_writes_backup(fake, tmp_path):
    uris = [f"spotify:track:{i}" for i in range(150)]
    api = fake([entry(u) for u in uris])
    spotify.cmd_replace(replace_args(tmp_path, list(reversed(uris))))
    writes = [c for c in api.calls if c[0] != "GET"]
    assert writes == [("PUT", 100), ("POST", 50)]
    backups = list((tmp_path / "backups").glob("P-*.json"))
    assert len(backups) == 1 and json.loads(backups[0].read_text())["uris"] == uris


def test_replace_refuses_when_local_files_would_be_lost(fake, tmp_path):
    api = fake([entry("spotify:track:a"), entry("spotify:local:x", local=True)])
    with pytest.raises(SystemExit):
        spotify.cmd_replace(replace_args(tmp_path, ["spotify:track:a"]))
    assert all(c[0] == "GET" for c in api.calls)


def test_replace_refuses_changed_multiset_without_flag(fake, tmp_path):
    api = fake([entry("spotify:track:a"), entry("spotify:track:a"), entry("spotify:track:b")])
    with pytest.raises(SystemExit):
        spotify.cmd_replace(replace_args(tmp_path, ["spotify:track:a", "spotify:track:b"]))  # drops a dup
    assert all(c[0] == "GET" for c in api.calls)
    spotify.cmd_replace(replace_args(tmp_path, ["spotify:track:a", "spotify:track:b"], allow=True))
    assert ("PUT", 2) in api.calls


def test_paths_expand_user(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    (tmp_path / "u.json").write_text(json.dumps(["spotify:track:a"]))
    assert spotify.load_uris("~/u.json") == ["spotify:track:a"]
    assert spotify.out_path("~/w/x.json", None) == tmp_path / "w" / "x.json"


def test_api_refuses_to_send_token_off_host(monkeypatch):
    monkeypatch.setattr(spotify, "access_token", lambda force_refresh=False: "tok")
    with pytest.raises(SystemExit):
        spotify.api("GET", "https://evil.example.com/v1/me")


def test_out_path_refuses_token_file():
    with pytest.raises(SystemExit):
        spotify.out_path(str(spotify.TOKEN_FILE), None)


def test_clean_lastfm_tags_drops_junk_and_low_counts():
    raw = [{"name": "Hip-Hop", "count": 100}, {"name": "seen live", "count": 80},
           {"name": "rap", "count": 50}, {"name": "drake", "count": 30}, {"name": "rare", "count": 2}]
    assert tagmod.clean_tags(raw, artist="Drake") == ["hip-hop", "rap"]
