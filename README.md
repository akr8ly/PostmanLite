# PostmanLite Automated Runner

A lightweight Streamlit runner for Postman Collection v2.1 JSON files. It runs requests sequentially, interpolates `{{variables}}`, shows live results, and exports HTML or Markdown reports.

## Quick Start

From PowerShell:

```powershell
cd D:\PostmanLite
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

In the browser, open the **Collection** tab, choose **Load included sample**, then open **Run** and select **Run collection**. Visit **Reports** to download the result. The sample calls public JSONPlaceholder endpoints, so it requires internet access.

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

Push these files to GitHub, create an app at Streamlit Community Cloud, choose the repository, and set the main file to `app.py`.
