#!/usr/bin/env python3
"""
Mass uploader that drives your FastAPI endpoints:
  POST /report/upload
  POST /report/embed
  POST /report/generate-tables

Usage:
  python mass_upload_via_api.py           # real run
  python mass_upload_via_api.py --dry-run  # only list files

Requirements:
  pip install requests
"""

import os
import sys
import time
import csv
import argparse
from pathlib import Path
from typing import Optional, Tuple, Dict
import requests

# ---------- CONFIG ----------
API_BASE_URL = "http://127.0.0.1:8000"
API_KEY = "a8861fce-c6e4-489e-9426-a8b12eca8c70" 

PDF_FOLDER = Path("app/mass_upload_files")
OUTPUT_CSV = Path("mass_upload_api_results.csv")

# header name used by your Streamlit front end
HEADERS = {"access-token": API_KEY}

# per-call retry settings
MAX_RETRIES = 4
INITIAL_BACKOFF = 1.0  # seconds
BACKOFF_MULTIPLIER = 2.0

# time to wait between files (a small throttling to be polite)
PER_FILE_DELAY = 0.5

# endpoints
UPLOAD_ENDPOINT = f"{API_BASE_URL}/report/upload"
EMBED_ENDPOINT = f"{API_BASE_URL}/report/embed"
TABLES_ENDPOINT = f"{API_BASE_URL}/report/generate-tables"
STATUS_ENDPOINT_TEMPLATE = f"{API_BASE_URL}/report/status/{{chatid}}"

# ---------- helpers ----------
def retry_post(url: str, files=None, data=None, json_payload=None, headers=None, max_retries=MAX_RETRIES) -> Optional[requests.Response]:
    attempt = 0
    backoff = INITIAL_BACKOFF
    while attempt < max_retries:
        try:
            attempt += 1
            resp = requests.post(url, headers=headers or HEADERS, files=files, data=data, json=json_payload, timeout=900)
            # return response regardless of HTTP status to let caller inspect codes/body
            return resp
        except requests.RequestException as e:
            print(f"[WARN] POST {url} attempt {attempt} failed: {e}. Retrying in {backoff}s...")
            time.sleep(backoff)
            backoff *= BACKOFF_MULTIPLIER
    return None

def safe_json(resp: Optional[requests.Response]) -> Optional[dict]:
    if resp is None:
        return None
    try:
        return resp.json()
    except Exception:
        return None

def call_upload(file_path: Path) -> Tuple[bool, Dict]:
    """
    Returns (success, response_data_or_error)
    """
    print(f" -> upload: {file_path.name}")
    with open(file_path, "rb") as fh:
        files = {"file": (file_path.name, fh, "application/pdf")}
        resp = retry_post(UPLOAD_ENDPOINT, files=files)
    if resp is None:
        return False, {"error": "no_response"}
    if resp.status_code >= 500:
        return False, {"error": f"server_error_{resp.status_code}", "text": resp.text}
    # Accept 200 OK with data
    data = safe_json(resp)
    if not data or data.get("error", True):
        # upload returned error or malformed JSON
        return False, {"error": "backend_error_or_malformed", "status_code": resp.status_code, "body": resp.text, "json": data}
    # expected structure: data: { "chatid": ..., "gu_id": ... }
    return True, data.get("data", {})

def call_embed(chatid: str, gu_id: str) -> Tuple[bool, Dict]:
    print(f" -> embed: chatid={chatid}, gu_id={gu_id}")
    payload = {"chatid": chatid, "gu_id": gu_id}
    resp = retry_post(EMBED_ENDPOINT, data=payload)
    if resp is None:
        return False, {"error": "no_response"}
    if resp.status_code >= 500:
        return False, {"error": f"server_error_{resp.status_code}", "text": resp.text}
    data = safe_json(resp)
    # embed may return error True/False - treat non-200 as failure
    if resp.status_code != 200 or data is None or data.get("error", True):
        return False, {"error": "embed_failed", "status_code": resp.status_code, "body": resp.text, "json": data}
    return True, data.get("data", {})

def call_generate_tables(chatid: str, gu_id: str) -> Tuple[bool, Dict]:
    print(f" -> generate-tables: chatid={chatid}, gu_id={gu_id}")
    payload = {"chatid": chatid, "gu_id": gu_id}
    resp = retry_post(TABLES_ENDPOINT, data=payload)
    if resp is None:
        return False, {"error": "no_response"}
    # 208 Already Reported is ok (means tables already generated)
    if resp.status_code == 208:
        return True, {"status": "already_generated"}
    if resp.status_code != 200:
        return False, {"error": f"tables_failed_status_{resp.status_code}", "body": resp.text}
    data = safe_json(resp)
    if data is None or data.get("error", True):
        return False, {"error": "tables_backend_error", "body": resp.text, "json": data}
    return True, data.get("data", {})

# ---------- main logic ----------
def process_all_files(dry_run: bool = False):
    pdfs = sorted(PDF_FOLDER.glob("*.pdf"))
    if not pdfs:
        print(f"[INFO] No PDF files found in {PDF_FOLDER}")
        return

    print(f"[INFO] Found {len(pdfs)} files in {PDF_FOLDER}. dry_run={dry_run}")

    results = []
    for pdf in pdfs:
        row = {
            "file": pdf.name,
            "upload_ok": False,
            "upload_info": None,
            "embed_ok": False,
            "embed_info": None,
            "tables_ok": False,
            "tables_info": None
        }

        if dry_run:
            print(f"[DRY] Would process: {pdf.name}")
            row["upload_info"] = "dry_run"
            results.append(row)
            continue

        # Step 1: upload
        upload_ok, upload_data = call_upload(pdf)
        row["upload_ok"] = bool(upload_ok)
        row["upload_info"] = upload_data
        if not upload_ok:
            print(f"[ERROR] Upload failed for {pdf.name}: {upload_data}")
            results.append(row)
            time.sleep(PER_FILE_DELAY)
            continue

        # Extract chatid and gu_id (accept strings)
        chatid = upload_data.get("chatid") or upload_data.get("chat_id") or upload_data.get("chatId")
        gu_id = upload_data.get("gu_id") or upload_data.get("file_id") or upload_data.get("fileId") or upload_data.get("guId")
        if not chatid or not gu_id:
            print(f"[ERROR] Upload succeeded but response missing chatid/gu_id: {upload_data}")
            results.append(row)
            time.sleep(PER_FILE_DELAY)
            continue

        # Step 2: embed (retryable)
        embed_ok, embed_data = call_embed(chatid=chatid, gu_id=gu_id)
        row["embed_ok"] = bool(embed_ok)
        row["embed_info"] = embed_data
        if not embed_ok:
            print(f"[ERROR] Embed failed for {pdf.name}: {embed_data}")
            results.append(row)
            time.sleep(PER_FILE_DELAY)
            continue

        # Step 3: generate tables
        tables_ok, tables_data = call_generate_tables(chatid=chatid, gu_id=gu_id)
        row["tables_ok"] = bool(tables_ok)
        row["tables_info"] = tables_data

        if not tables_ok:
            print(f"[ERROR] Table generation failed for {pdf.name}: {tables_data}")
        else:
            print(f"[OK] Processed {pdf.name} successfully.")

        results.append(row)
        time.sleep(PER_FILE_DELAY)

    # write CSV summary
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "file", "upload_ok", "upload_info", "embed_ok", "embed_info", "tables_ok", "tables_info"
        ])
        writer.writeheader()
        for r in results:
            # convert dicts to short strings for CSV
            r2 = r.copy()
            for k in ["upload_info", "embed_info", "tables_info"]:
                v = r2.get(k)
                if isinstance(v, dict):
                    # keep short structured string
                    r2[k] = str(v)
                else:
                    r2[k] = v
            writer.writerow(r2)

    print(f"[DONE] Results written to {OUTPUT_CSV}")

# ---------- entry ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mass upload PDFs via your app endpoints")
    parser.add_argument("--dry-run", action="store_true", help="Only list files")
    args = parser.parse_args()
    process_all_files(dry_run=args.dry_run)
