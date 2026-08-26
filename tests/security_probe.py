from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor

import requests
from fastapi import HTTPException
from pydantic import ValidationError

from backend.server import PostmanExecutor, RunPayload, ensure_allowed_url, validate_collection


MODE = "local" if os.getenv("POSTMANLITE_ALLOW_PRIVATE_NETWORKS", "false").lower() == "true" else "hosted"
RESULTS: list[dict[str, object]] = []


def record(name: str, passed: bool, detail: str, category: str = "policy") -> None:
    RESULTS.append({"mode": MODE, "name": name, "passed": passed, "category": category, "detail": detail[:500]})


def policy_case(name: str, url: str, should_allow: bool) -> None:
    try:
        ensure_allowed_url(url)
        record(name, should_allow, "allowed")
    except ValueError as exc:
        record(name, not should_allow, f"blocked: {exc}")


def request_case(name: str, url: str, should_succeed: bool = True, timeout: int = 8) -> None:
    item = {"request": {"method": "GET", "url": url}}
    result = PostmanExecutor({}, timeout).run_request(name, item)
    passed = result.ok if should_succeed else not result.ok
    record(name, passed, f"status={result.status}; error={result.error or '-'}; preview={len(result.preview)}", "network")


private_allowed = MODE == "local"
policy_case("public HTTPS policy", "https://jsonplaceholder.typicode.com/posts/1", True)
policy_case("public HTTP policy", "http://neverssl.com/", True)
policy_case("public raw IPv4 policy", "http://1.1.1.1/", True)
policy_case("IPv4 localhost policy", "http://127.0.0.1:8080/health", private_allowed)
policy_case("localhost hostname policy", "http://localhost:8080/health", private_allowed)
policy_case("IPv6 localhost policy", "http://[::1]:8080/health", private_allowed)
policy_case("10/8 private policy", "http://10.0.0.1/", private_allowed)
policy_case("192.168/16 private policy", "http://192.168.1.1/", private_allowed)
policy_case("link-local metadata policy", "http://169.254.169.254/", private_allowed)
policy_case("FTP rejected", "ftp://example.com/file", False)
policy_case("file URL rejected", "file:///etc/hosts", False)
policy_case("invalid hostname rejected", "http://does-not-exist.invalid/", False)

request_case("public HTTPS request", "https://jsonplaceholder.typicode.com/posts/1")
request_case("public HTTP request", "http://neverssl.com/")
request_case("raw public IPv4 request", "http://1.1.1.1/", timeout=8)
request_case("self-signed TLS behavior", "https://self-signed.badssl.com/", should_succeed=os.getenv("POSTMANLITE_ALLOW_INSECURE_TLS", "false").lower() == "true")
request_case("expired TLS behavior", "https://expired.badssl.com/", should_succeed=os.getenv("POSTMANLITE_ALLOW_INSECURE_TLS", "false").lower() == "true")
request_case("wrong-host TLS behavior", "https://wrong.host.badssl.com/", should_succeed=os.getenv("POSTMANLITE_ALLOW_INSECURE_TLS", "false").lower() == "true")
request_case("DNS failure behavior", "http://does-not-exist.invalid/", should_succeed=False)
request_case("redirect loop behavior", "https://httpbin.org/redirect/5", should_succeed=False)
request_case(
    "public-to-private redirect follows local policy",
    "https://httpbin.org/redirect-to?url=http://127.0.0.1:8080/health",
    should_succeed=private_allowed,
)
request_case("malformed JSON handled as text", "https://httpbin.org/html")
request_case("binary response handled", "https://httpbin.org/bytes/64")
request_case("large response preview capped", "https://httpbin.org/bytes/2100000", timeout=15)

if MODE == "local":
    request_case("localhost reachable", "http://127.0.0.1:8080/health")
    request_case("closed local port fails", "http://127.0.0.1:59999/", should_succeed=False, timeout=2)
    request_case("IPv6 localhost reachability", "http://[::1]:8080/health", timeout=2)
else:
    request_case("localhost request blocked", "http://127.0.0.1:8080/health", should_succeed=False)

for name, collection in [
    ("missing info rejected", {"item": []}),
    ("missing item rejected", {"info": {"name": "bad"}}),
    ("empty collection rejected", {"info": {"name": "empty"}, "item": []}),
    ("26-request collection rejected", {"info": {"name": "large"}, "item": [{"name": str(i), "request": {"method": "GET", "url": "https://example.com"}} for i in range(26)]}),
]:
    try:
        validate_collection(collection)
        record(name, False, "accepted unexpectedly", "validation")
    except HTTPException as exc:
        record(name, True, f"HTTP {exc.status_code}: {exc.detail}", "validation")

unsupported = PostmanExecutor({}, 2).run_request("TRACE", {"request": {"method": "TRACE", "url": "https://example.com"}})
record("unsupported TRACE rejected", not unsupported.ok and "not allowed" in unsupported.error, unsupported.error, "validation")

try:
    RunPayload(collection={"info": {"name": "x"}, "item": []}, timeout=31)
    record("timeout above 30 rejected", False, "accepted unexpectedly", "validation")
except ValidationError as exc:
    record("timeout above 30 rejected", True, str(exc).splitlines()[0], "validation")

try:
    responses = list(ThreadPoolExecutor(max_workers=5).map(lambda _: requests.get("http://127.0.0.1:8080/health", timeout=3).status_code, range(5)))
    record("five concurrent health requests", responses == [200] * 5, str(responses), "concurrency")
except requests.RequestException as exc:
    record("five concurrent health requests", False, str(exc), "concurrency")

print(json.dumps(RESULTS, indent=2))
