# ZimaOS app store

A personal app store for ZimaOS / CasaOS with my own apps:

| App | Image | Port |
|---|---|---|
| [Youtubaar](https://github.com/mystikxkemix/Youtubaar) | `ghcr.io/mystikxkemix/youtubaar` | 8085 |
| [SelfHoster](https://github.com/mystikxkemix/self-hoster) | `ghcr.io/mystikxkemix/self-hoster` | 8090 |
| [Bank tracking](https://github.com/mystikxkemix/bank-tracking) | `ghcr.io/mystikxkemix/bank-tracking` | 8095 |

## Add it to ZimaOS

App Store → **+** (add source) → paste:

```
https://mystikxkemix.github.io/zimaos-appstore
```

ZimaOS only accepts stores in the v2 protocol (a static site with `store.json` and
`index.json`); a zip URL is refused with "Unsupported import method".

## How it is built

The **Publish store** workflow runs on every push, every hour and on demand:

1. `scripts/bump_images.py` checks ghcr.io for a newer `1.N` image of each app, then
   writes the image tag and `x-casaos.version` (`1.N.0`) and commits them.
2. The official [`IceWhaleTech/build-appstore-action`](https://github.com/IceWhaleTech/build-appstore-action)
   builds the v2 store into `dist/`.
3. `dist/` goes to the `gh-pages` branch, served by GitHub Pages.

ZimaOS offers an update when an app's `x-casaos.version` goes up. The images must be
public: ZimaOS pulls them without a login, and so does the workflow.

## Layout

```
Apps/<app>/docker-compose.yml   compose + top-level x-casaos metadata
Apps/<app>/icon.svg
store-config.json               store id, name, maintainer
supported-languages.json
```

Format reference: [ZimaOS AppStore docs](https://github.com/IceWhaleTech/CasaOS-AppStore/tree/main/docs).
