from __future__ import annotations

import html
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import streamlit as st
from jsonschema import Draft7Validator

st.set_page_config(page_title="PostmanLite", page_icon="⚡", layout="wide")


def apply_app_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {
            --pl-bg: #080806;
            --pl-panel: rgba(18, 18, 14, .72);
            --pl-panel-strong: #12120e;
            --pl-amber: #ffb000;
            --pl-orange: #ff6b35;
            --pl-text: #e8e6e1;
            --pl-muted: #8a8a7c;
            --pl-border: rgba(255, 176, 0, .16);
        }

        html, body, [class*="css"] {font-family: 'Inter', system-ui, sans-serif;}
        .stApp {
            color: var(--pl-text);
            background:
                radial-gradient(circle at 12% 8%, rgba(255,176,0,.09), transparent 27rem),
                radial-gradient(circle at 88% 30%, rgba(255,107,53,.07), transparent 30rem),
                linear-gradient(180deg, #080806 0%, #0b0b09 55%, #080806 100%);
            background-attachment: fixed;
        }
        header[data-testid="stHeader"] {background: rgba(8,8,6,.78); backdrop-filter: blur(16px);}
        #MainMenu, footer {display: none;}
        .stMainBlockContainer {max-width: 1120px; padding-top: 3.25rem; padding-bottom: 5rem;}

        h1, h2, h3, label, p, .stMarkdown {color: var(--pl-text);}
        h1 {
            font-weight: 800;
            max-width: 900px;
            color: #f4f1e9 !important;
            font-size: clamp(3rem, 6vw, 5.25rem) !important;
            line-height: 1.02 !important;
            letter-spacing: -.06em;
            background: none;
            -webkit-text-fill-color: currentColor;
        }
        h2 {font-weight: 700; letter-spacing: -.025em; padding-top: .35rem;}
        [data-testid="stCaptionContainer"], [data-testid="stWidgetLabel"] p {color: var(--pl-muted);}
        hr {border-color: var(--pl-border) !important;}
        code, pre, [data-testid="stCode"] * {font-family: 'JetBrains Mono', monospace !important;}

        [data-testid="stFileUploader"], [data-testid="stDataFrame"],
        [data-testid="stExpander"], [data-testid="stAlert"], [data-testid="stCode"] {
            border: 1px solid var(--pl-border);
            border-radius: 14px;
            background: var(--pl-panel);
            box-shadow: 0 16px 44px rgba(0,0,0,.22);
        }
        [data-testid="stFileUploaderDropzone"] {
            background: rgba(255,176,0,.035);
            border-color: rgba(255,176,0,.25);
        }
        [data-testid="stFileUploader"] > label {display: none;}
        [data-testid="stTextInputRootElement"], [data-baseweb="textarea"], [data-baseweb="input"],
        [data-baseweb="base-input"], [data-baseweb="input"] > div {
            color: var(--pl-text) !important;
            background: rgba(18,18,14,.72) !important;
            border-color: var(--pl-border) !important;
            border-radius: 9px !important;
        }
        input, textarea {color: var(--pl-text) !important; caret-color: var(--pl-amber);}
        input:focus, textarea:focus {border-color: var(--pl-amber) !important;}

        .stButton > button, .stDownloadButton > button {
            color: var(--pl-text);
            background: rgba(255,176,0,.06);
            border: 1px solid rgba(255,176,0,.28);
            border-radius: 9px;
            font-weight: 600;
            transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            color: #fff;
            border-color: var(--pl-amber);
            transform: translateY(-1px);
            box-shadow: 0 8px 26px rgba(255,176,0,.12);
        }
        .stButton > button[kind="primary"] {
            color: #100b00;
            border: 0;
            background: linear-gradient(110deg, var(--pl-amber), var(--pl-orange));
            box-shadow: 0 10px 28px rgba(255,107,53,.2);
        }
        [data-testid="stProgress"] > div > div > div > div {
            background: linear-gradient(90deg, var(--pl-amber), var(--pl-orange));
        }
        [data-testid="stExpander"] details summary:hover {color: var(--pl-amber);}
        [data-testid="stDataFrame"] {overflow: hidden;}
        [data-testid="stAlert"] {
            color: var(--pl-text) !important;
            background: rgba(18,18,14,.68) !important;
            border-color: rgba(255,176,0,.13) !important;
            box-shadow: inset 3px 0 0 rgba(255,176,0,.42), 0 16px 44px rgba(0,0,0,.18);
        }
        [data-testid="stAlert"] > div,
        [data-testid="stAlert"] [data-baseweb="notification"] {
            color: var(--pl-text) !important;
            background: transparent !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_app_theme()

COLLECTION_SCHEMA = {
    "type": "object", "required": ["info", "item"],
    "properties": {"info": {"type": "object", "required": ["name"]}, "item": {"type": "array"}},
}
VAR = re.compile(r"{{\s*([^{}\s]+)\s*}}")


@dataclass
class Result:
    name: str; method: str; url: str; status: int | None; elapsed_ms: int
    ok: bool; error: str = ""; preview: str = ""


def flatten(items: list[dict[str, Any]], prefix: str = "") -> list[tuple[str, dict[str, Any]]]:
    output = []
    for item in items:
        label = f"{prefix} / {item.get('name', 'Unnamed')}".strip(" / ")
        if "item" in item:
            output.extend(flatten(item["item"], label))
        elif "request" in item:
            output.append((label, item))
    return output


def variables_from(collection: dict[str, Any], supplied: dict[str, str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for entry in collection.get("variable", []):
        if entry.get("key"):
            values[entry["key"]] = str(entry.get("value", ""))
    values.update({k: str(v) for k, v in supplied.items() if k})
    return values


def interpolate(value: Any, variables: dict[str, str]) -> Any:
    if not isinstance(value, str): return value
    return VAR.sub(lambda m: variables.get(m.group(1), m.group(0)), value)


def header_dict(headers: list[dict[str, Any]], variables: dict[str, str]) -> dict[str, str]:
    return {interpolate(h.get("key", ""), variables): interpolate(h.get("value", ""), variables)
            for h in headers if h.get("key") and not h.get("disabled")}

def trim_payload(data: Any, max_items: int = 3) -> Any:
    if isinstance(data, list):
        return [trim_payload(item, max_items) for item in data[:max_items]]
    elif isinstance(data, dict):
        return {k: trim_payload(v, max_items) for k, v in data.items()}
    return data


class PostmanExecutor:
    def __init__(self, variables: dict[str, str], timeout: int):
        self.variables, self.timeout = variables, timeout
        self.session = requests.Session()

    def run_request(self, name: str, item: dict[str, Any]) -> Result:
        request = item["request"]
        method = request.get("method", "GET").upper()
        raw_url = request.get("url", "")
        if isinstance(raw_url, dict): raw_url = raw_url.get("raw") or raw_url.get("href", "")
        url = interpolate(raw_url, self.variables)
        kwargs: dict[str, Any] = {"headers": header_dict(request.get("header", []), self.variables), "timeout": self.timeout}
        body = request.get("body", {})
        if body and not body.get("disabled"):
            mode = body.get("mode")
            if mode == "raw": kwargs["data"] = interpolate(body.get("raw", ""), self.variables)
            elif mode == "urlencoded": kwargs["data"] = {interpolate(x.get("key", ""), self.variables): interpolate(x.get("value", ""), self.variables) for x in body.get("urlencoded", []) if x.get("key") and not x.get("disabled")}
            elif mode == "formdata": kwargs["data"] = {interpolate(x.get("key", ""), self.variables): interpolate(x.get("value", ""), self.variables) for x in body.get("formdata", []) if x.get("key") and not x.get("disabled") and x.get("type", "text") == "text"}
        started = time.perf_counter()
        try:
            response = self.session.request(method, url, **kwargs)
            elapsed = int((time.perf_counter() - started) * 1000)
            try:
                payload = response.json()
                preview = json.dumps(trim_payload(payload, 3), indent=2)
                # Make top-level JSON response fields available to later requests as {{field}}.
                if isinstance(payload, dict):
                    self.variables.update({k: str(v) for k, v in payload.items() if isinstance(v, (str, int, float, bool))})
            except (ValueError, TypeError): 
                preview = response.text[:1000]
            return Result(name, method, url, response.status_code, elapsed, response.ok, preview=preview)
        except requests.RequestException as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            return Result(name, method, url, None, elapsed, False, error=str(exc))


def markdown_report(results: list[Result], title: str) -> str:
    lines = [f"# {title} — Run report", "", f"Generated: {datetime.now().isoformat(timespec='seconds')}", "", "| Request | Method | Status | Time | Result |", "|---|---|---:|---:|---|"]
    lines += [f"| {r.name} | {r.method} | {r.status or '—'} | {r.elapsed_ms} ms | {'PASS' if r.ok else 'FAIL'} |" for r in results]
    return "\n".join(lines)


def html_report(results: list[Result], title: str) -> str:
    rows = "".join(f"<tr><td>{html.escape(r.name)}</td><td>{r.method}</td><td>{r.status or '—'}</td><td>{r.elapsed_ms} ms</td><td class='{('pass' if r.ok else 'fail')}'>{'PASS' if r.ok else 'FAIL'}</td></tr>" for r in results)
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)} report</title><style>body{{font:14px system-ui;margin:32px;color:#18212f}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #dce1e7;padding:10px;text-align:left}}th{{background:#f5f7fa}}.pass{{color:#137333;font-weight:bold}}.fail{{color:#b3261e;font-weight:bold}}</style></head><body><h1>{html.escape(title)} — Run report</h1><p>Generated: {datetime.now().isoformat(timespec='seconds')}</p><table><tr><th>Request</th><th>Method</th><th>Status</th><th>Time</th><th>Result</th></tr>{rows}</table></body></html>"""


def parse_environment(text: str) -> dict[str, str]:
    try:
        data = json.loads(text or "{}")
        if not isinstance(data, dict): raise ValueError("must be a JSON object")
        return {str(k): str(v) for k, v in data.items()}
    except (json.JSONDecodeError, ValueError) as exc:
        st.error(f"Environment variables must be a JSON object: {exc}")
        return {}


st.title("⚡ PostmanLite Automated Runner")
st.caption("Upload a Postman Collection v2.1 export, set variables, and run requests sequentially.")
if "collection" not in st.session_state: st.session_state.collection = None
if "results" not in st.session_state: st.session_state.results = []

st.header("1. Collection")
file = st.file_uploader("Postman collection (.json)", type="json")
url = st.text_input("Or load from a URL (e.g., raw GitHub link or Postman public link)")
left, right = st.columns(2)
with left:
    if st.button("Load included sample"):
        sample_path = Path(__file__).with_name("sample_collection.json")
        with sample_path.open(encoding="utf-8") as fh: st.session_state.collection = json.load(fh)
with right:
    if st.button("Load from URL"):
        if url:
            try:
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict) and "info" in data and "item" in data:
                    st.session_state.collection = data
                else:
                    raise ValueError("Not a Postman collection")
            except Exception:
                st.session_state.collection = {
                    "info": {"name": "Quick URL Test", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
                    "item": [{"name": url, "request": {"url": url, "method": "GET"}}]
                }
                st.info("Interpreted URL as a direct API endpoint. Generated a quick test.")
        else:
            st.warning("Please enter a URL first.")
if file:
    try: st.session_state.collection = json.load(file)
    except json.JSONDecodeError as exc: st.error(f"Invalid JSON: {exc}")
collection = st.session_state.collection
if collection:
    errors = list(Draft7Validator(COLLECTION_SCHEMA).iter_errors(collection))
    if errors: st.error("Not a valid Postman collection: " + "; ".join(e.message for e in errors))
    else:
        requests_found = flatten(collection["item"])
        st.success(f"Loaded **{collection['info']['name']}** — {len(requests_found)} request(s) found.")
        st.dataframe([{"Request": n, "Method": x["request"].get("method", "GET")} for n, x in requests_found], hide_index=True, use_container_width=True)

st.divider()
st.header("2. Run")
collection = st.session_state.collection
if not collection: st.info("Upload or load a collection above.")
else:
    env_text = st.text_area("Environment variables (JSON)", value=json.dumps({v.get("key"): v.get("value", "") for v in collection.get("variable", []) if v.get("key")}, indent=2), height=150, help="Values override collection variables. Use them as {{variable_name}}.")
    timeout = st.number_input("Request timeout (seconds)", min_value=1, max_value=300, value=30)
    if st.button("Run collection", type="primary"):
        supplied = parse_environment(env_text)
        if supplied is not None:
            executor = PostmanExecutor(variables_from(collection, supplied), int(timeout))
            items = flatten(collection["item"]); results: list[Result] = []
            progress = st.progress(0); log = st.empty()
            for index, (name, item) in enumerate(items, 1):
                log.info(f"Running {index}/{len(items)}: {name}")
                result = executor.run_request(name, item); results.append(result)
                (log.success if result.ok else log.error)(f"{result.method} {result.url} → {result.status or 'ERROR'} ({result.elapsed_ms} ms){': ' + result.error if result.error else ''}")
                progress.progress(index / len(items))
            st.session_state.results = results
            st.session_state.report_title = collection["info"]["name"]
            st.success(f"Finished: {sum(r.ok for r in results)}/{len(results)} passed.")
    if st.session_state.results:
        st.subheader("Latest results")
        st.dataframe([asdict(r) for r in st.session_state.results], hide_index=True, use_container_width=True)
        for r in st.session_state.results:
            with st.expander(f"{r.method} {r.name} — {'PASS' if r.ok else 'FAIL'}"):
                st.code(r.error or r.preview or "No response body", language="json")

st.divider()
st.header("3. Reports")
results = st.session_state.results
if not results: st.info("Run a collection to generate reports.")
else:
    title = st.session_state.get("report_title", "PostmanLite")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Download Markdown report", markdown_report(results, title), "postmanlite-report.md", "text/markdown", use_container_width=True)
    with col2:
        st.download_button("Download HTML report", html_report(results, title), "postmanlite-report.html", "text/html", use_container_width=True)
    st.subheader("Report Preview")
    st.markdown(markdown_report(results, title))
