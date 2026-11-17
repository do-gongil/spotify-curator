# spotify-curator

English · [한국어](README.md) · **[Tutorial](TUTORIAL.en.md)**

A plugin that builds playlists that fit you.

| Skill | What it does | Example prompt |
|---|---|---|
| `genre-curate` | Collect tracks of similar genres from chosen playlists (or Liked Songs) into a new playlist | "Collect only the jazz from playlists A and B" |
| `playlist-from-prompt` | Short description → Claude proposes candidates → verified via Spotify search → playlist created | "Make a 25-song rainy-night city pop playlist" |
| `playlist-mix` | Split a playlist into sub-playlists by similarity group, or reorder it so similar songs flow together (auto backup) | "Split my playlist by genre" |
| `playlist-report` | Genre distribution, artist concentration, duplicates (read-only) | "Analyze my Liked Songs" |
| `setup` | Step-by-step key setup, login and checks (`doctor`) | "set up spotify-curator" |
| `playlist-extend` | Recommend, verify and add N tracks matching a playlist's vibe | "Add 10 similar songs to this playlist" |

Skill instructions and outputs are primarily Korean, but English requests work too.

## Requirements
- Python 3.7+ (`python` or `python3`)
- Spotify **Premium** account (required for Dev Mode apps since 2026-02)
- Claude Code

## Setup (once)

**Easiest:** after installing, tell Claude Code "set up spotify-curator", then get the API keys and enter them. Full walkthrough: [Tutorial](TUTORIAL.en.md).
Manual steps below. Instead of env vars you can run `python scripts/spotify.py setup` (interactive) to save keys to `~/.spotify-curator/config.json`; env vars take precedence. Check with `python scripts/spotify.py doctor`.

1. **Spotify app**
   - https://developer.spotify.com/dashboard → Create app → API: *Web API*
   - Redirect URI: `http://127.0.0.1:8888/callback` (`localhost` is not allowed).
     If port 8888 is taken (e.g. Jupyter), register another port and set `SPOTIFY_REDIRECT_PORT` to match
   - Add your Spotify account email under the app's **User Management** (otherwise you get 403)
   - Set the Client ID as env var `SPOTIFY_CLIENT_ID` (PKCE flow, no client secret needed)
2. **Last.fm API key** (for genre tags, free): https://www.last.fm/api/account/create → `LASTFM_API_KEY`
3. **Restart your terminal / Claude Code** after setting env vars.

   Windows (PowerShell):
   ```powershell
   [Environment]::SetEnvironmentVariable("SPOTIFY_CLIENT_ID", "<client id>", "User")
   [Environment]::SetEnvironmentVariable("LASTFM_API_KEY", "<key>", "User")
   ```
   macOS / Linux (`~/.zshrc` or `~/.bashrc`):
   ```sh
   export SPOTIFY_CLIENT_ID="<client id>"
   export LASTFM_API_KEY="<key>"
   ```
4. Log in: `python scripts/spotify.py login` (approve in browser). The refresh token expires 6 months after first approval; log in again then.

## Install

In Claude Code:
```
/plugin marketplace add do-gongil/spotify-curator
/plugin install spotify-curator@spotify-curator
```
If login is needed while a skill runs, Claude prints the exact command to run.
For development: clone the repo and run `claude --plugin-dir <clone path>`.

## Data & security
- Data lives in `~/.spotify-curator/` (`config.json`, `token.json`, `tags_cache.json`, `work/`, `backups/`); override with `SPOTIFY_CURATOR_HOME`
- `config.json` (keys) and `token.json` are stored in **plain text** (0600 on POSIX). Keep it out of shared folders
- Log out: delete `token.json` and revoke the app under Spotify account settings → Apps
- New playlists are private. No delete command. Reorders are backed up first

## Layout
- `scripts/spotify.py` — dependency-free Web API CLI (`python scripts/spotify.py -h`)
- `scripts/tags.py` — artist → genre tags (Last.fm, falling back to Spotify genres), cached in `~/.spotify-curator/tags_cache.json`
- `scripts/group.py` — tag → main genre mapping, grouping, similarity ordering. Fix wrong mappings in the `EXACT`/`SUBSTR` tables

## Limitations (Spotify Web API, new Dev Mode apps)
- Refer to playlists by name
- Only playlists you **own or collaborate on** can be read (not followed or Spotify-generated ones)
- audio-features / recommendations / related-artists are unavailable → similarity is genre-tag based; recommendations come from Claude + search verification
- Spotify Dev Mode does not return artist genres → relies on Last.fm tags. Different artists can share a name (e.g. Dori, used by both a male and a female singer-songwriter).
- Dev Mode: personal, non-commercial use, max 5 users per app
- Playlist deletion isn't supported (endpoint changed 2026-02) → delete in the Spotify app
- `replace` (reorder) resets each track's "date added". Playlists containing local files/episodes are refused
- This tool is for personal curation and does not use data for training

## Tests
```
python -m pytest tests -q
```

## License
MIT
