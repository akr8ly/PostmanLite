# PostmanLite Automated Runner

A lightweight Streamlit runner for Postman Collection v2.1 JSON files. It runs requests sequentially, interpolates `{{variables}}`, shows live results, and exports HTML or Markdown reports.

## Project structure

```text
PostmanLite/
├── backend/
│   ├── app.py                  # Streamlit API runner
│   ├── requirements.txt        # Python dependencies
│   └── sample_collection.json  # Included demo collection
├── frontend/
│   ├── landing.html            # Marketing landing page
│   ├── app.html                # Full-window runner shell
│   └── serve.py                # Local frontend server
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

The frontend and backend are separate local processes. Keep both PowerShell windows open.

### PowerShell window 1 — backend

```powershell
cd D:\PostmanLite
.\.venv\Scripts\python.exe -m streamlit run .\backend\app.py
```

### PowerShell window 2 — frontend

```powershell
cd D:\PostmanLite
.\.venv\Scripts\python.exe .\frontend\serve.py
```

Open `http://localhost:8080`. The landing page is served as a full browser page, and **Launch PostmanLite** opens the runner at `/app.html` on the same visible site.

Load the included sample, run the collection, and use **Reports** to download the result. The user interface and runner are local, but the included sample calls public JSONPlaceholder endpoints and therefore requires internet access.

> **Note:** If `python` is not recognized, install Python 3.10 or newer and reopen PowerShell. If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` for the current terminal only.

## Variables

Collection variables and the JSON environment field are merged; environment values take precedence. For example:

```json
{"base_url": "https://api.example.com", "token": "abc123"}
```

Use `{{base_url}}` or `{{token}}` in URLs, headers, and request bodies. Top-level primitive fields from a JSON response are automatically available to subsequent requests, such as `{{id}}`.

## Supported collection features

- Nested folders and GET, POST, PUT, PATCH, DELETE requests
- URL, header, raw, form-url-encoded, and text form-data interpolation
- Basic collection structure validation and connection/timeout errors

Postman scripts, assertions, file uploads, cookies, OAuth flows, and full Postman environments are intentionally outside this MVP's scope.

## Streamlit Community Cloud

Push these files to GitHub, create an app at Streamlit Community Cloud, choose the repository, and set the main file to `backend/app.py`.

## Render

The repository includes `render.yaml` for deploying the Streamlit backend from the `master` branch. In Render, create a **Blueprint** from this repository to apply the correct Python version, dependency path, start command, and health check automatically.

If configuring a Render web service manually instead, leave the root directory blank and use:

```text
Build command: pip install -r backend/requirements.txt
Start command: streamlit run backend/app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true
```
