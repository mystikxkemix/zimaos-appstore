# ZimaOS app store

A personal app store for ZimaOS / CasaOS with my own apps:

| App | Image | Port |
|---|---|---|
| [Youtubaar](https://github.com/mystikxkemix/Youtubaar) | `ghcr.io/mystikxkemix/youtubaar` | 8085 |
| [SelfHoster](https://github.com/mystikxkemix/self-hoster) | `ghcr.io/mystikxkemix/self-hoster` | 8090 |
| [Bank tracking](https://github.com/mystikxkemix/bank-tracking) | `ghcr.io/mystikxkemix/bank-tracking` | 8095 |
| [Family API](https://github.com/mystikxkemix/family-app) | `ghcr.io/mystikxkemix/family-api` | 8100 |

## Add it to ZimaOS

App Store → **+** (add source) → paste:

```
https://mystikxkemix.github.io/zimaos-appstore
```

ZimaOS only accepts stores in the v2 protocol (a static site with `store.json` and
`index.json`); a zip URL is refused with "Unsupported import method".

## How it is built

The **Publish store** workflow runs on every push, every hour and on demand:

1. `scripts/bump_images.py` checks ghcr.io for a newer `M.N` image of each app (compared as numbers, so `2.21` is newer than `1.37`), then
   writes the image tag and `x-casaos.version` (`M.N.0`) and commits them. The apps tag their images `2.<merges into master>` (+1 per merged PR; it was `1.<all commits>` before).
2. The official [`IceWhaleTech/build-appstore-action`](https://github.com/IceWhaleTech/build-appstore-action)
   builds the v2 store into `dist/`.
3. `dist/` goes to the `gh-pages` branch, served by GitHub Pages.

ZimaOS offers an update when an app's `x-casaos.version` goes up.

### Release notes

With each bump, the script also writes `x-casaos.release_notes` and `update_at`, so
ZimaOS shows what changed. Nothing to do in the app repositories:

- Each image gives its git commit and repository in its OCI labels
  (`org.opencontainers.image.revision` and `.source`, set by `docker/metadata-action`).
- The notes list the commits between the old image and the new one with a
  conventional type: `feat` (New), `fix` (Fix), `perf` (Faster). Merges, `docs`,
  `ci`, `chore`, `refactor`... are skipped. So write commit subjects for a reader.
- An app without notes gets the notes of its current version (compared with the
  previous `M.N` image). If the old commit is gone (rewritten history), the notes
  only link to the commits.
- Notes are in English (`en_US`), at most 15 lines, with a link to the full compare. The images must be
public: ZimaOS pulls them without a login, and so does the workflow.

## Layout

```
Apps/<app>/docker-compose.yml   compose + top-level x-casaos metadata
Apps/<app>/icon.svg
store-config.json               store id, name, maintainer
supported-languages.json
```

Format reference: [ZimaOS AppStore docs](https://github.com/IceWhaleTech/CasaOS-AppStore/tree/main/docs).
