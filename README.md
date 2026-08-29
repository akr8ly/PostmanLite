# PostmanLite Automated Runner

A single-service API testing workspace for Postman Collection v2.1 JSON files. FastAPI serves the landing page, browser workspace, and protected request-execution API from one origin.

## Project structure

```text
PostmanLite/
├── requirements.txt            # Deployment dependency shim
├── backend/
│   ├── server.py               # FastAPI server and request runner
│   ├── requirements.txt        # Python dependencies
│   └── sample_collection.json  # Included demo collection
├── frontend/
│   ├── index.html              # Marketing landing page
│   └── app.html                # Native API workspace
├── render.yaml                  # Single-service Render deployment
└── README.md
```

## Local setup

Run the following once from PowerShell:

```powershell
cd D:\PostmanLite
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
```

## Start locally

The complete website runs from one process:

```powershell
cd D:\PostmanLite
.\.venv\Scripts\python.exe -m uvicorn backend.server:app --host 127.0.0.1 --port 8080 --reload
```

Open `http://localhost:8080` for the landing page. **Launch PostmanLite** opens the workspace at `/app` on the same origin.

Load the included sample, run the collection, and use **Reports** to download the result. The user interface and runner are local, but the included sample calls public JSONPlaceholder endpoints and therefore requires internet access.

### Local and private APIs

Plain HTTP endpoints are supported by default. To allow `localhost`, raw private IPs, and RFC 1918 networks in a trusted local/self-hosted installation, start PowerShell with:

```powershell
$env:POSTMANLITE_ALLOW_PRIVATE_NETWORKS = "true"
.\.venv\Scripts\python.exe -m uvicorn backend.server:app --host 127.0.0.1 --port 8080 --reload
```

For a development server using a self-signed HTTPS certificate, you can additionally set:

```powershell
$env:POSTMANLITE_ALLOW_INSECURE_TLS = "true"
```

Insecure TLS disables certificate verification and should never be enabled on the public Render service. A hosted PostmanLite process also cannot access services bound only to your personal computer's localhost; run PostmanLite locally for that use case.

### IPv4 and IPv6 localhost on Windows

On Windows, Uvicorn's `::` listener can be IPv6-only. To expose the same local port through both address families, run these in two PowerShell windows:

```powershell
# IPv6 listener
$env:POSTMANLITE_ALLOW_PRIVATE_NETWORKS = "true"
.\.venv\Scripts\python.exe -m uvicorn backend.server:app --host :: --port 8080
```

```powershell
# IPv4 listener
$env:POSTMANLITE_ALLOW_PRIVATE_NETWORKS = "true"
.\.venv\Scripts\python.exe -m uvicorn backend.server:app --host 0.0.0.0 --port 8080
```

This was verified with HTTP 200 responses from `http://[::1]:8080/health`, `http://127.0.0.1:8080/health`, and `http://localhost:8080/health`. Keep Render on a single `0.0.0.0` listener.

> **Note:** If `python` is not recognized, install Python 3.10 or newer and reopen PowerShell. If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` for the current terminal only.

## Variables

Collection variables and the JSON environment field are merged; environment values take precedence. For example:

```json
{"base_url": "https://api.example.com", "token": "abc123"}
```

Use `{{base_url}}` or `{{token}}` in URLs, headers, and request bodies. Top-level primitive fields from a JSON response are automatically available to subsequent requests, such as `{{id}}`.

## Supported collection features

- Nested folders and GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS, and RFC 10008 QUERY requests
- URL, header, raw, form-url-encoded, and text form-data interpolation
- Basic collection structure validation and connection/timeout errors

Postman scripts, assertions, file uploads, cookies, OAuth flows, and full Postman environments are intentionally outside this MVP's scope.

## Render

The repository includes `render.yaml` for a single Render web service from the `master` branch. The same public domain serves `/`, `/app`, and `/api/*`.

If configuring a Render web service manually instead, leave the root directory blank and use:

```text
Build command: pip install -r backend/requirements.txt
Start command: uvicorn backend.server:app --host 0.0.0.0 --port $PORT
```

Hosted mode blocks private/local/reserved destinations by default, revalidates redirects, limits collections to 25 requests, caps remote response previews, and limits per-request timeout to 30 seconds. Public production access should additionally add authentication, persistent rate limiting, audit logging, and a restrictive outbound network policy.
