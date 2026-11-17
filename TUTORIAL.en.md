# Tutorial

English · [한국어](TUTORIAL.md) · [README](README.en.md)

From install to your first playlist in about 10 minutes.

## 0. Prerequisites
- Spotify **Premium** account
- Claude Code
- Python 3.7+ (check with `python --version` or `python3 --version`)

## 1. Install the plugin
In Claude Code:
```
/plugin marketplace add do-gongil/spotify-curator
/plugin install spotify-curator@spotify-curator
```

## 2. Setup (let Claude drive)
Tell Claude Code:
```
set up spotify-curator
```
Claude walks you through it with the `setup` skill. The only manual part is getting keys from two websites.

### 2-1. Create a Spotify app (you)
1. Log in at https://developer.spotify.com/dashboard → **Create app**
2. Any name/description; set **Redirect URI** to `http://127.0.0.1:8888/callback` and click Add
3. Under **Which API/SDKs**, check *Web API* → accept the terms → Save
4. App → **Settings** → **User Management**: add your Spotify account email (otherwise 403)
5. Copy the **Client ID** (32 chars) from Settings and paste it to Claude

> The Client ID is not a secret. No client secret is needed.

### 2-2. Get a Last.fm API key (you)
1. https://www.last.fm/api/account/create (Last.fm account required)
2. Enter just an application name and submit → copy the **API key**
3. This key is a secret; pasting it in chat keeps it in the conversation log. To avoid that, run this yourself in the Claude Code prompt:
   ```
   ! python "<plugin path>/scripts/spotify.py" setup
   ```
   (Input is hidden. Claude will tell you the path.)

### 2-3. Log in and check (Claude runs these)
- Claude runs `spotify.py login`; a browser opens → click **Agree**
- Then `spotify.py doctor` checks everything (output labels are Korean):
  ```
  [OK]   Spotify Client ID
  [OK]   Last.fm API key
  [OK]   Spotify 로그인 (name)
  [OK]   Spotify API 접근
  준비 완료
  ```

Settings are saved to `~/.spotify-curator/config.json`, so no env vars or terminal restart are needed.

## 3. Try it

| Goal | Say |
|---|---|
| New playlist from a description | "Make a 25-song nostalgic playlist like DPR IAN" |
| Collect a genre from your playlists | "Collect only the R&B from playlists A and B into a new one" |
| Analyze | "Show the genre distribution and duplicates in my Liked Songs" |
| Split / reorder | "Split this playlist by genre", "Reorder so similar songs flow together" |
| Add similar songs | "Add 10 similar songs to Faded Polaroids" |

Claude always shows the track list and asks before changing anything on Spotify. Reorders are backed up first.

## 4. Troubleshooting
Say "check spotify-curator" and Claude runs `doctor` to find the cause.

| Symptom | Cause / fix |
|---|---|
| 403 error | Email not in User Management, or not Premium |
| `INVALID_CLIENT: Invalid redirect URI` | The Dashboard Redirect URI must exactly match `http://127.0.0.1:8888/callback` (`localhost` not allowed) |
| Login port in use | Add another port (e.g. 8899) as a Redirect URI, then `setup --port 8899` |
| Token expired | 6 months after first approval. Run `spotify.py login` again |
| Wrong genre grouping | Last.fm tag issue. Say e.g. "set Crush to k-rnb" to override |
| Followed playlists can't be read | Spotify API limit. Only playlists you own or collaborate on |

## 5. Log out / uninstall
- Delete the `~/.spotify-curator/` folder (token, config, cache, backups)
- Spotify account settings → **Apps**: remove access
- `/plugin uninstall spotify-curator`
