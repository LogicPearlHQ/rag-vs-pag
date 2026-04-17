from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


API_ROOT = "https://www.muckrock.com/api_v2"
TOKEN_URL = "https://accounts.muckrock.com/api/token/"


@dataclass
class MuckRockClient:
    token: str
    user_agent: str = "LogicPearl rag-vs-pag research demo"

    @classmethod
    def from_env(cls) -> "MuckRockClient":
        token = os.getenv("MUCKROCK_JWT")
        if token:
            return cls(token=token)
        username = os.getenv("MUCKROCK_USERNAME")
        password = os.getenv("MUCKROCK_PASSWORD")
        if not username or not password:
            raise RuntimeError("set MUCKROCK_JWT or MUCKROCK_USERNAME/MUCKROCK_PASSWORD")
        body = json.dumps({"username": username, "password": password}).encode("utf-8")
        request = urllib.request.Request(
            TOKEN_URL,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": cls.user_agent},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return cls(token=payload["access"])

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = {"format": "json", **(params or {})}
        query = urllib.parse.urlencode(params)
        url = f"{API_ROOT}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{query}"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "User-Agent": self.user_agent,
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def download(self, url: str) -> bytes:
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "User-Agent": self.user_agent,
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()


@dataclass
class PublicMuckRockClient:
    user_agent: str = "LogicPearl rag-vs-pag research demo"

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = {"format": "json", **(params or {})}
        query = urllib.parse.urlencode(params)
        url = f"{API_ROOT}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{query}"
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def download(self, url: str) -> bytes:
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
