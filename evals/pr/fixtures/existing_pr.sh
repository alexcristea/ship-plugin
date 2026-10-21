#!/bin/bash
# feat/upload-exports already has open PR #57 for the S3 upload; two newer commits adding retries aren't pushed yet.
source "$(dirname "$0")/../base.sh" "$1"
git switch -q -c feat/upload-exports
cat > widget/upload.py <<'P'
import urllib.request


def upload(text, presigned_url):
    """PUT an export to S3 through a presigned URL."""
    req = urllib.request.Request(presigned_url, data=text.encode(), method="PUT")
    with urllib.request.urlopen(req) as resp:
        return resp.status
P
git add -A; c 3 "feat(export): upload exports to S3 through a presigned URL"
git push -q -u origin feat/upload-exports
open_pr <<'J'
{
  "number": 57,
  "title": "feat(export): upload exports to S3",
  "body": "## Summary\n\nUploads each export to S3 through a presigned URL, so scheduled exports no longer need a shared drive.\n\n## Testing\n\n- [ ] Upload a small report to a test bucket",
  "url": "https://github.com/acme/widget/pull/57",
  "state": "OPEN",
  "headRefName": "feat/upload-exports",
  "baseRefName": "main",
  "isDraft": false
}
J
cat > widget/upload.py <<'P'
import time
import urllib.error
import urllib.request


def upload(text, presigned_url, attempts=3):
    """PUT an export to S3 through a presigned URL, retrying 5xx responses with exponential backoff."""
    req = urllib.request.Request(presigned_url, data=text.encode(), method="PUT")
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)
P
git add -A; c 4 "feat(export): retry failed uploads with exponential backoff"
cat > tests/test_upload.py <<'P'
import unittest
from unittest import mock

from widget import upload


class Upload(unittest.TestCase):
    @mock.patch("time.sleep")
    @mock.patch("urllib.request.urlopen")
    def test_retries_server_errors(self, urlopen, _):
        import urllib.error
        ok = mock.MagicMock(); ok.__enter__.return_value.status = 200
        urlopen.side_effect = [urllib.error.HTTPError("u", 503, "busy", {}, None), ok]
        self.assertEqual(upload.upload("x", "https://s3/x"), 200)
P
git add -A; c 5 "test(export): cover upload retries"
record_pr
