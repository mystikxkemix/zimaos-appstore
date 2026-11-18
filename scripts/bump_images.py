#!/usr/bin/env python3
"""Raise each app's ghcr.io image to its newest 1.N tag.

Reads Apps/*/docker-compose.yml, asks ghcr.io (anonymous, so the package must be
public) for the image's tags, and rewrites the line when a newer 1.N tag exists.
ZimaOS then sees a new version of the app in this store and offers the update.
Prints one line per change; exits 0 even when an image cannot be read.
"""
import json
import pathlib
import re
import sys
import urllib.request

IMAGE = re.compile(r"^(\s*image:\s*ghcr\.io/)([\w.-]+/[\w.-]+):(\S+)\s*$", re.M)
VERSION = re.compile(r"^1\.(\d+)$")


def tags(repository: str) -> list[str]:
    token_url = f"https://ghcr.io/token?scope=repository:{repository}:pull"
    with urllib.request.urlopen(token_url, timeout=30) as response:
        token = json.load(response)["token"]
    request = urllib.request.Request(
        f"https://ghcr.io/v2/{repository}/tags/list?n=1000",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response).get("tags") or []


def newest(candidates: list[str]) -> str | None:
    numbers = [int(match.group(1)) for tag in candidates if (match := VERSION.match(tag))]
    return f"1.{max(numbers)}" if numbers else None


def main() -> int:
    for compose in sorted(pathlib.Path("Apps").glob("*/docker-compose.yml")):
        text = compose.read_text()
        match = IMAGE.search(text)
        if match is None:
            continue
        repository, current = match.group(2), match.group(3)
        try:
            latest = newest(tags(repository))
        except Exception as error:  # a private or missing package must not stop the others
            print(f"{compose}: cannot list {repository} tags ({error})", file=sys.stderr)
            continue
        current_match = VERSION.match(current)
        if latest is None or (current_match and int(latest[2:]) <= int(current_match.group(1))):
            continue
        compose.write_text(text[: match.start()] + f"{match.group(1)}{repository}:{latest}\n" + text[match.end() + 1 :])
        print(f"{compose.parent.name} {current} -> {latest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
