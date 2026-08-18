# Quick start

From PowerShell:

```powershell
cd D:\PostmanLite
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

In the browser, open the **Collection** tab, choose **Load included sample**, then open **Run** and select **Run collection**. Visit **Reports** to download the result.

If `python` is not recognized, install Python 3.10 or newer and reopen PowerShell. If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` for the current terminal only.
