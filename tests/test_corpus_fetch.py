import hashlib
import http.server
import threading
from pathlib import Path

import pytest

from corpus.fetch import FetchError, fetch_one


@pytest.fixture
def local_server(tmp_path):
    payload = b"hello foia corpus\n"
    (tmp_path / "file.txt").write_bytes(payload)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args, **kwargs):  # silence
            pass

    import os

    cwd = os.getcwd()
    os.chdir(tmp_path)
    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}/file.txt", hashlib.sha256(payload).hexdigest()
    finally:
        srv.shutdown()
        os.chdir(cwd)


def test_fetch_one_success(tmp_path, local_server):
    url, sha = local_server
    out = tmp_path / "out.bin"
    observed = fetch_one(url, sha, out)
    assert observed == sha
    assert out.read_bytes() == b"hello foia corpus\n"


def test_fetch_one_sha_mismatch_raises(tmp_path, local_server):
    url, _ = local_server
    out = tmp_path / "out.bin"
    with pytest.raises(FetchError, match="sha256 mismatch"):
        fetch_one(url, "0" * 64, out)


def test_fetch_one_tbd_accepts_any(tmp_path, local_server):
    url, _ = local_server
    out = tmp_path / "out.bin"
    observed = fetch_one(url, "TBD", out)
    assert len(observed) == 64
