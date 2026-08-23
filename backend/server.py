from __future__ import annotations

import ipaddress, json, re, socket, time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from jsonschema import Draft7Validator
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]; FRONTEND = ROOT / "frontend"; SAMPLE = Path(__file__).with_name("sample_collection.json")
MAX_REQUESTS = 25; MAX_REMOTE_BYTES = 2_000_000
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
VAR = re.compile(r"{{\s*([^{}\s]+)\s*}}")
COLLECTION_SCHEMA = {"type":"object","required":["info","item"],"properties":{"info":{"type":"object","required":["name"]},"item":{"type":"array"}}}
app = FastAPI(title="PostmanLite", docs_url=None, redoc_url=None)

class LoadPayload(BaseModel): url: str = Field(min_length=1, max_length=2048)
class RunPayload(BaseModel):
    collection: dict[str, Any]; environment: dict[str, Any] = Field(default_factory=dict); timeout: int = Field(default=30, ge=1, le=30)
@dataclass
class Result:
    name: str; method: str; url: str; status: int | None; elapsed_ms: int; ok: bool; error: str = ""; preview: str = ""

def flatten(items: list[dict[str, Any]], prefix: str = "") -> list[tuple[str, dict[str, Any]]]:
    output = []
    for item in items:
        label = f"{prefix} / {item.get('name', 'Unnamed')}".strip(" / ")
        if isinstance(item.get("item"), list): output.extend(flatten(item["item"], label))
        elif isinstance(item.get("request"), dict): output.append((label, item))
    return output

def validate_collection(collection: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    errors = list(Draft7Validator(COLLECTION_SCHEMA).iter_errors(collection))
    if errors: raise HTTPException(422, "; ".join(error.message for error in errors))
    items = flatten(collection["item"])
    if not items: raise HTTPException(422, "Collection contains no executable requests")
    if len(items) > MAX_REQUESTS: raise HTTPException(422, f"Collections are limited to {MAX_REQUESTS} requests")
    return items

def interpolate(value: Any, variables: dict[str, str]) -> Any:
    return VAR.sub(lambda match: variables.get(match.group(1), match.group(0)), value) if isinstance(value, str) else value

def variables_from(collection: dict[str, Any], supplied: dict[str, Any]) -> dict[str, str]:
    values = {str(v["key"]):str(v.get("value", "")) for v in collection.get("variable",[]) if isinstance(v,dict) and v.get("key")}
    values.update({str(k):str(v) for k,v in supplied.items() if k}); return values

def ensure_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http","https"} or not parsed.hostname: raise ValueError("Only public HTTP and HTTPS URLs are allowed")
    try: addresses = {info[4][0] for info in socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))}
    except socket.gaierror as exc: raise ValueError("Hostname could not be resolved") from exc
    if any(not ipaddress.ip_address(address).is_global for address in addresses): raise ValueError("Private, local, and reserved network targets are blocked")
    return url

def request_public(session: requests.Session, method: str, url: str, **kwargs: Any) -> requests.Response:
    current = ensure_public_url(url)
    for _ in range(4):
        response = session.request(method, current, allow_redirects=False, **kwargs)
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("location"); response.close()
            if not location: raise requests.RequestException("Redirect had no destination")
            current = ensure_public_url(urljoin(current, location)); continue
        return response
    raise requests.TooManyRedirects("Too many redirects")

def trim_payload(data: Any) -> Any:
    if isinstance(data,list): return [trim_payload(v) for v in data[:3]]
    if isinstance(data,dict): return {k:trim_payload(v) for k,v in data.items()}
    return data

class PostmanExecutor:
    def __init__(self, variables: dict[str,str], timeout: int): self.variables=variables; self.timeout=timeout; self.session=requests.Session()
    def run_request(self, name: str, item: dict[str,Any]) -> Result:
        request=item["request"]; method=str(request.get("method","GET")).upper()
        if method not in ALLOWED_METHODS: return Result(name,method,"",None,0,False,error="HTTP method is not allowed")
        raw_url=request.get("url",""); raw_url=raw_url.get("raw") or raw_url.get("href","") if isinstance(raw_url,dict) else raw_url
        url=interpolate(raw_url,self.variables)
        headers={interpolate(h.get("key",""),self.variables):interpolate(h.get("value",""),self.variables) for h in request.get("header",[]) if isinstance(h,dict) and h.get("key") and not h.get("disabled")}
        kwargs: dict[str,Any]={"headers":headers,"timeout":self.timeout}; body=request.get("body",{})
        if body and not body.get("disabled"):
            mode=body.get("mode")
            if mode=="raw": kwargs["data"]=interpolate(body.get("raw",""),self.variables)
            elif mode in {"urlencoded","formdata"}: kwargs["data"]={interpolate(e.get("key",""),self.variables):interpolate(e.get("value",""),self.variables) for e in body.get(mode,[]) if e.get("key") and not e.get("disabled") and (mode!="formdata" or e.get("type","text")=="text")}
        started=time.perf_counter()
        try:
            response=request_public(self.session,method,url,**kwargs); elapsed=int((time.perf_counter()-started)*1000); content=response.content[:MAX_REMOTE_BYTES]
            try:
                payload=json.loads(content); preview=json.dumps(trim_payload(payload),indent=2)
                if isinstance(payload,dict): self.variables.update({k:str(v) for k,v in payload.items() if isinstance(v,(str,int,float,bool))})
            except (ValueError,TypeError,UnicodeDecodeError): preview=content.decode(response.encoding or "utf-8",errors="replace")[:4000]
            return Result(name,method,url,response.status_code,elapsed,response.ok,preview=preview)
        except (requests.RequestException,ValueError) as exc: return Result(name,method,url,None,int((time.perf_counter()-started)*1000),False,error=str(exc))

@app.get("/",include_in_schema=False)
def landing_page(): return FileResponse(FRONTEND/"index.html")
@app.get("/app",include_in_schema=False)
def app_page(): return FileResponse(FRONTEND/"app.html")
@app.get("/app.html",include_in_schema=False)
def legacy_app_page(): return RedirectResponse("/app",status_code=308)
@app.get("/health")
def health(): return {"status":"ok"}
@app.get("/api/sample")
def sample_collection(): return JSONResponse(json.loads(SAMPLE.read_text(encoding="utf-8")))
@app.post("/api/collections/load")
def load_collection(payload: LoadPayload):
    try:
        with requests.Session() as session:
            response=request_public(session,"GET",payload.url,timeout=10); response.raise_for_status()
            if len(response.content)>MAX_REMOTE_BYTES: raise HTTPException(413,"Remote collection is too large")
            data=response.json()
    except HTTPException: raise
    except (requests.RequestException,ValueError) as exc: raise HTTPException(400,str(exc)) from exc
    validate_collection(data); return data
@app.post("/api/run")
def run_collection(payload: RunPayload):
    items=validate_collection(payload.collection); executor=PostmanExecutor(variables_from(payload.collection,payload.environment),payload.timeout)
    results=[asdict(executor.run_request(name,item)) for name,item in items]
    return {"title":str(payload.collection["info"]["name"]),"passed":sum(r["ok"] for r in results),"total":len(results),"results":results}
