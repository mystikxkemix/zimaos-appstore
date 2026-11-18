# ZimaOS app store

A personal app store for ZimaOS / CasaOS with my own apps:

| App | Image | Port |
|---|---|---|
| [Youtubaar](https://github.com/mystikxkemix/Youtubaar) | `ghcr.io/mystikxkemix/youtubaar` | 8085 |
| [SelfHoster](https://github.com/mystikxkemix/self-hoster) | `ghcr.io/mystikxkemix/self-hoster` | 8090 |

## Add it to ZimaOS

App Store → **+** (add source) → paste:

```
https://github.com/mystikxkemix/zimaos-appstore/archive/refs/heads/main.zip
```

## Updates

Each app's CI publishes a `1.<number of commits>` image. The **Bump images** workflow
checks ghcr.io every hour (or on demand), writes the newest `1.N` tag into the app's
`docker-compose.yml` and commits it. ZimaOS then shows the update.

The images must be public: ZimaOS pulls them without a login, and so does the workflow.

## Layout

CasaOS AppStore format: `Apps/<app>/docker-compose.yml` with an `x-casaos` block
(title, icon, category, port), plus `category-list.json` and `recommend-list.json`.
