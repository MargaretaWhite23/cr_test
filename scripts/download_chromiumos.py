#!/usr/bin/env python3
"""Download the newest published official amd64-generic-vm-public ChromiumOS image."""
import json
import pathlib
import re
import sys
import tarfile
import urllib.parse
import urllib.request

destination = pathlib.Path(sys.argv[1])
destination.mkdir(parents=True, exist_ok=True)
bucket = "chromiumos-image-archive"
prefix = "amd64-generic-vm-public/"
url = (
    f"https://storage.googleapis.com/storage/v1/b/{bucket}/o?"
    + urllib.parse.urlencode({"prefix": prefix, "fields": "nextPageToken,items(name)", "maxResults": 1000})
)
objects = []
while url:
    with urllib.request.urlopen(url, timeout=90) as response:
        page = json.load(response)
    objects.extend(item["name"] for item in page.get("items", []))
    token = page.get("nextPageToken")
    url = (
        f"https://storage.googleapis.com/storage/v1/b/{bucket}/o?"
        + urllib.parse.urlencode({"prefix": prefix, "fields": "nextPageToken,items(name)", "maxResults": 1000, "pageToken": token})
        if token else None
    )
matches = []
for name in objects:
    m = re.fullmatch(r"amd64-generic-vm-public/R(\d+)-(\d+)\.(\d+)\.(\d+)/chromiumos_test_image\.tar\.xz", name)
    if m:
        matches.append((tuple(map(int, m.groups())), name))
if not matches:
    raise SystemExit("No official ChromiumOS prebuilt VM images found in public bucket.")
version, object_name = max(matches)
print(f"Selected latest published image: {object_name}", flush=True)
archive = destination / "chromiumos_test_image.tar.xz"
download_url = f"https://storage.googleapis.com/{bucket}/{urllib.parse.quote(object_name)}"
with urllib.request.urlopen(download_url, timeout=120) as response, archive.open("wb") as output:
    while chunk := response.read(1024 * 1024):
        output.write(chunk)
print(f"Downloaded {archive.stat().st_size} bytes", flush=True)
with tarfile.open(archive, "r:xz") as tf:
    members = [m for m in tf.getmembers() if m.isfile() and pathlib.PurePosixPath(m.name).name == "chromiumos_test_image.bin"]
    if len(members) != 1:
        raise SystemExit("Expected exactly one chromiumos_test_image.bin")
    with tf.extractfile(members[0]) as source, (destination / "chromiumos_test_image.bin").open("wb") as target:
        while chunk := source.read(1024 * 1024):
            target.write(chunk)
archive.unlink()
print("Extracted ChromiumOS disk image", flush=True)
