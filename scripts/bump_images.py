#!/usr/bin/env python3
"""Raise each app's ghcr.io image to its newest 1.N tag and write its release notes.

Reads Apps/*/docker-compose.yml, asks ghcr.io (anonymous, so the package must be
public) for the image's tags, and when a newer 1.N tag exists rewrites the image
line and x-casaos.version ("1.N.0", semver as the v2 store protocol wants).
ZimaOS compares that version with the installed one and offers the update.

It also writes x-casaos.release_notes (shown by ZimaOS with the update) and
x-casaos.update_at. The notes are the conventional commits (feat, fix, perf) of
the app repository between the old image and the new one. Each image gives its
commit and repository in its OCI labels (org.opencontainers.image.revision and
.source, set by docker/metadata-action). An app without notes gets the notes of
its current version, compared with the previous 1.N image.

Reading GitHub uses $GH_TOKEN when it is set (the workflow passes its token),
otherwise anonymous calls (60 per hour).
Prints one line per change; exits 0 even when an image or a repository cannot be read.
"""
import datetime
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

IMAGE = re.compile(r"^(\s*image:\s*ghcr\.io/)([\w.-]+/[\w.-]+):(\S+)\s*$", re.M)
VERSION = re.compile(r"^1\.(\d+)$")
APP_VERSION = re.compile(r'^(  version:\s*)"?[^"\n]*"?\s*$', re.M)
# The update_at line and the release_notes block (its lines are indented by 4+ spaces).
OLD_NOTES = re.compile(r'^  (?:update_at:.*|release_notes:.*(?:\n {4,}.*)*)\n', re.M)
COMMIT = re.compile(r"^(feat|fix|perf)(?:\(([^)]*)\))?!?:\s*(.+)$")
KINDS = {"feat": "New", "fix": "Fix", "perf": "Faster"}
MAX_LINES = 15
MANIFESTS = ",".join([
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
])


def fetch_json(url: str, headers: dict[str, str]) -> dict:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def registry_token(repository: str) -> str:
    return fetch_json(f"https://ghcr.io/token?scope=repository:{repository}:pull", {})["token"]


def tags(repository: str, token: str) -> list[str]:
    answer = fetch_json(f"https://ghcr.io/v2/{repository}/tags/list?n=1000", {"Authorization": f"Bearer {token}"})
    return answer.get("tags") or []


def numbers(candidates: list[str]) -> list[int]:
    return sorted(int(match.group(1)) for tag in candidates if (match := VERSION.match(tag)))


def image_labels(repository: str, tag: str, token: str) -> dict[str, str]:
    """Returns the OCI labels of an image (the first real platform of a multi-arch image)."""
    headers = {"Authorization": f"Bearer {token}", "Accept": MANIFESTS}
    manifest = fetch_json(f"https://ghcr.io/v2/{repository}/manifests/{tag}", headers)
    if "manifests" in manifest:
        # Attestations are listed as platform "unknown/unknown": skip them.
        platforms = [entry for entry in manifest["manifests"] if entry.get("platform", {}).get("os") != "unknown"]
        manifest = fetch_json(f"https://ghcr.io/v2/{repository}/manifests/{platforms[0]['digest']}", headers)
    config = fetch_json(f"https://ghcr.io/v2/{repository}/blobs/{manifest['config']['digest']}",
                        {"Authorization": f"Bearer {token}"})
    return config.get("config", {}).get("Labels") or {}


def github_repository(source: str) -> str:
    """Turns https://github.com/owner/repo(.git) into owner/repo."""
    path = source.removeprefix("https://github.com/").removesuffix(".git").strip("/")
    if path == source or path.count("/") != 1:
        raise ValueError(f"not a GitHub repository: {source}")
    return path


def compare(repository: str, base: str, head: str) -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return fetch_json(f"https://api.github.com/repos/{repository}/compare/{base}...{head}", headers)


def note_lines(commits: list[dict]) -> list[str]:
    """One line per feat / fix / perf commit, oldest first. Merges, docs, ci... are skipped."""
    lines = []
    for commit in commits:
        subject = commit["commit"]["message"].split("\n", 1)[0].strip()
        match = COMMIT.match(subject)
        if match is None:
            continue
        kind, scope, text = match.groups()
        line = f"- {KINDS[kind]}: {text[0].upper()}{text[1:]}"
        if scope:
            line += f" ({scope})"
        lines.append(line)
    return lines


def release_notes(image_repository: str, token: str, base_tag: str, head_tag: str) -> tuple[str, str]:
    """Returns (notes, date) for the changes between two image tags."""
    head = image_labels(image_repository, head_tag, token)
    base = image_labels(image_repository, base_tag, token)
    repository = github_repository(head["org.opencontainers.image.source"])
    base_commit = base["org.opencontainers.image.revision"][:7]
    head_commit = head["org.opencontainers.image.revision"][:7]
    link = f"https://github.com/{repository}/compare/{base_commit}...{head_commit}"
    try:
        commits = compare(repository, base_commit, head_commit).get("commits") or []
        lines = note_lines(commits) or ["- Maintenance only, no visible change."]
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        # 404: the old commit is not in the history any more (history rewritten).
        commits = []
        lines = ["- The list of changes is not available for this update."]
        link = f"https://github.com/{repository}/commits/{head_commit}"
    if len(lines) > MAX_LINES:
        lines = lines[-MAX_LINES:] + [f"- And {len(lines) - MAX_LINES} older changes."]
    lines.insert(0, f"Changes since {base_tag}:")
    lines.append(link)
    date = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    if commits:
        date = commits[-1]["commit"]["committer"]["date"][:10]
    return "\n".join(lines), date


def with_notes(text: str, notes: str, date: str) -> str:
    """Replaces update_at and release_notes, written right after the version line."""
    text = OLD_NOTES.sub("", text)
    block = "".join(f"      {line}\n" for line in notes.split("\n"))
    addition = f'  update_at: "{date}"\n  release_notes:\n    en_US: |-\n{block}'
    match = APP_VERSION.search(text)
    if match is None:
        return text
    end = match.end() + 1
    return text[:end] + addition + text[end:]


def main() -> int:
    for compose in sorted(pathlib.Path("Apps").glob("*/docker-compose.yml")):
        text = compose.read_text()
        match = IMAGE.search(text)
        if match is None:
            continue
        repository, current = match.group(2), match.group(3)
        try:
            token = registry_token(repository)
            available = numbers(tags(repository, token))
        except Exception as error:  # a private or missing package must not stop the others
            print(f"{compose}: cannot list {repository} tags ({error})", file=sys.stderr)
            continue
        if not available:
            continue
        latest = f"1.{available[-1]}"
        current_match = VERSION.match(current)
        bumped = current_match is None or available[-1] > int(current_match.group(1))
        has_notes = re.search(r"^  release_notes:", text, re.M) is not None

        if bumped:
            text = text[: match.start()] + f"{match.group(1)}{repository}:{latest}\n" + text[match.end() + 1 :]
            text, count = APP_VERSION.subn(lambda found: f'{found.group(1)}"{latest}.0"', text, count=1)
            if count == 0:
                print(f"{compose}: no x-casaos version line to update", file=sys.stderr)
            # Notes from the version the store offered before; else from the previous image.
            base = current if current_match and current != latest else None
        elif has_notes:
            continue
        else:
            base = None
        if base is None:
            older = [number for number in available if number < available[-1]]
            base = f"1.{older[-1]}" if older else None

        change = f"{compose.parent.name} {current} -> {latest}" if bumped else f"{compose.parent.name} {latest} release notes"
        if base is not None:
            try:
                notes, date = release_notes(repository, token, base, latest)
                text = with_notes(text, notes, date)
            except Exception as error:  # notes are a bonus: the bump still happens
                print(f"{compose}: cannot write release notes ({error})", file=sys.stderr)
                if not bumped:
                    continue
        elif not bumped:
            continue
        compose.write_text(text)
        print(change)
    return 0


if __name__ == "__main__":
    sys.exit(main())
