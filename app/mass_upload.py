# #!/usr/bin/env python3
# """
# Mass uploader that drives your FastAPI endpoints:
#   POST /report/upload
#   POST /report/embed
#   POST /report/generate-tables

# Usage:
#   python mass_upload_via_api.py           # real run
#   python mass_upload_via_api.py --dry-run  # only list files

# Requirements:
#   pip install requests
# """

# import os
# import sys
# import time
# import csv
# import argparse
# from pathlib import Path
# from typing import Optional, Tuple, Dict
# import requests

# # ---------- CONFIG ----------
# API_BASE_URL = "http://127.0.0.1:8000"
# API_KEY = "a8861fce-c6e4-489e-9426-a8b12eca8c70" 

# PDF_FOLDER = Path("app/mass_upload_files")
# OUTPUT_CSV = Path("mass_upload_api_results.csv")

# # header name used by your Streamlit front end
# HEADERS = {"access-token": API_KEY}

# # per-call retry settings
# MAX_RETRIES = 4
# INITIAL_BACKOFF = 1.0  # seconds
# BACKOFF_MULTIPLIER = 2.0

# # time to wait between files (a small throttling to be polite)
# PER_FILE_DELAY = 0.5

# # endpoints
# UPLOAD_ENDPOINT = f"{API_BASE_URL}/report/upload"
# EMBED_ENDPOINT = f"{API_BASE_URL}/report/embed"
# TABLES_ENDPOINT = f"{API_BASE_URL}/report/generate-tables"
# STATUS_ENDPOINT_TEMPLATE = f"{API_BASE_URL}/report/status/{{chatid}}"

# # ---------- helpers ----------
# def retry_post(url: str, files=None, data=None, json_payload=None, headers=None, max_retries=MAX_RETRIES) -> Optional[requests.Response]:
#     attempt = 0
#     backoff = INITIAL_BACKOFF
#     while attempt < max_retries:
#         try:
#             attempt += 1
#             resp = requests.post(url, headers=headers or HEADERS, files=files, data=data, json=json_payload, timeout=300)
#             # return response regardless of HTTP status to let caller inspect codes/body
#             return resp
#         except requests.RequestException as e:
#             print(f"[WARN] POST {url} attempt {attempt} failed: {e}. Retrying in {backoff}s...")
#             time.sleep(backoff)
#             backoff *= BACKOFF_MULTIPLIER
#     return None

# def safe_json(resp: Optional[requests.Response]) -> Optional[dict]:
#     if resp is None:
#         return None
#     try:
#         return resp.json()
#     except Exception:
#         return None

# def call_upload(file_path: Path) -> Tuple[bool, Dict]:
#     """
#     Returns (success, response_data_or_error)
#     """
#     print(f" -> upload: {file_path.name}")
#     with open(file_path, "rb") as fh:
#         files = {"file": (file_path.name, fh, "application/pdf")}
#         resp = retry_post(UPLOAD_ENDPOINT, files=files)
#     if resp is None:
#         return False, {"error": "no_response"}
#     if resp.status_code >= 500:
#         return False, {"error": f"server_error_{resp.status_code}", "text": resp.text}
#     # Accept 200 OK with data
#     data = safe_json(resp)
#     if not data or data.get("error", True):
#         # upload returned error or malformed JSON
#         return False, {"error": "backend_error_or_malformed", "status_code": resp.status_code, "body": resp.text, "json": data}
#     # expected structure: data: { "chatid": ..., "gu_id": ... }
#     return True, data.get("data", {})

# def call_embed(chatid: str, gu_id: str) -> Tuple[bool, Dict]:
#     print(f" -> embed: chatid={chatid}, gu_id={gu_id}")
#     payload = {"chatid": chatid, "gu_id": gu_id}
#     resp = retry_post(EMBED_ENDPOINT, data=payload)
#     if resp is None:
#         return False, {"error": "no_response"}
#     if resp.status_code >= 500:
#         return False, {"error": f"server_error_{resp.status_code}", "text": resp.text}
#     data = safe_json(resp)
#     # embed may return error True/False - treat non-200 as failure
#     if resp.status_code != 200 or data is None or data.get("error", True):
#         return False, {"error": "embed_failed", "status_code": resp.status_code, "body": resp.text, "json": data}
#     return True, data.get("data", {})

# def call_generate_tables(chatid: str, gu_id: str) -> Tuple[bool, Dict]:
#     print(f" -> generate-tables: chatid={chatid}, gu_id={gu_id}")
#     payload = {"chatid": chatid, "gu_id": gu_id}
#     resp = retry_post(TABLES_ENDPOINT, data=payload)
#     if resp is None:
#         return False, {"error": "no_response"}
#     # 208 Already Reported is ok (means tables already generated)
#     if resp.status_code == 208:
#         return True, {"status": "already_generated"}
#     if resp.status_code != 200:
#         return False, {"error": f"tables_failed_status_{resp.status_code}", "body": resp.text}
#     data = safe_json(resp)
#     if data is None or data.get("error", True):
#         return False, {"error": "tables_backend_error", "body": resp.text, "json": data}
#     return True, data.get("data", {})

# # ---------- main logic ----------
# def process_all_files(dry_run: bool = False):
#     pdfs = sorted(PDF_FOLDER.glob("*.pdf"))
#     if not pdfs:
#         print(f"[INFO] No PDF files found in {PDF_FOLDER}")
#         return

#     print(f"[INFO] Found {len(pdfs)} files in {PDF_FOLDER}. dry_run={dry_run}")

#     results = []
#     for pdf in pdfs:
#         row = {
#             "file": pdf.name,
#             "upload_ok": False,
#             "upload_info": None,
#             "embed_ok": False,
#             "embed_info": None,
#             "tables_ok": False,
#             "tables_info": None
#         }

#         if dry_run:
#             print(f"[DRY] Would process: {pdf.name}")
#             row["upload_info"] = "dry_run"
#             results.append(row)
#             continue

#         # Step 1: upload
#         upload_ok, upload_data = call_upload(pdf)
#         row["upload_ok"] = bool(upload_ok)
#         row["upload_info"] = upload_data
#         if not upload_ok:
#             print(f"[ERROR] Upload failed for {pdf.name}: {upload_data}")
#             results.append(row)
#             time.sleep(PER_FILE_DELAY)
#             continue

#         # Extract chatid and gu_id (accept strings)
#         chatid = upload_data.get("chatid") or upload_data.get("chat_id") or upload_data.get("chatId")
#         gu_id = upload_data.get("gu_id") or upload_data.get("file_id") or upload_data.get("fileId") or upload_data.get("guId")
#         if not chatid or not gu_id:
#             print(f"[ERROR] Upload succeeded but response missing chatid/gu_id: {upload_data}")
#             results.append(row)
#             time.sleep(PER_FILE_DELAY)
#             continue

#         # Step 2: embed (retryable)
#         embed_ok, embed_data = call_embed(chatid=chatid, gu_id=gu_id)
#         row["embed_ok"] = bool(embed_ok)
#         row["embed_info"] = embed_data
#         if not embed_ok:
#             print(f"[ERROR] Embed failed for {pdf.name}: {embed_data}")
#             results.append(row)
#             time.sleep(PER_FILE_DELAY)
#             continue

#         # Step 3: generate tables
#         tables_ok, tables_data = call_generate_tables(chatid=chatid, gu_id=gu_id)
#         row["tables_ok"] = bool(tables_ok)
#         row["tables_info"] = tables_data

#         if not tables_ok:
#             print(f"[ERROR] Table generation failed for {pdf.name}: {tables_data}")
#         else:
#             print(f"[OK] Processed {pdf.name} successfully.")

#         results.append(row)
#         time.sleep(PER_FILE_DELAY)

#     # write CSV summary
#     with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fh:
#         writer = csv.DictWriter(fh, fieldnames=[
#             "file", "upload_ok", "upload_info", "embed_ok", "embed_info", "tables_ok", "tables_info"
#         ])
#         writer.writeheader()
#         for r in results:
#             # convert dicts to short strings for CSV
#             r2 = r.copy()
#             for k in ["upload_info", "embed_info", "tables_info"]:
#                 v = r2.get(k)
#                 if isinstance(v, dict):
#                     # keep short structured string
#                     r2[k] = str(v)
#                 else:
#                     r2[k] = v
#             writer.writerow(r2)

#     print(f"[DONE] Results written to {OUTPUT_CSV}")

# # ---------- entry ----------
# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Mass upload PDFs via your app endpoints")
#     parser.add_argument("--dry-run", action="store_true", help="Only list files")
#     args = parser.parse_args()
#     process_all_files(dry_run=args.dry_run)




#####    with GLOBAL RETRY LOOP  ####
#!/usr/bin/env python3
"""
Mass uploader with AUTO-RETRY logic.
It drives your FastAPI endpoints:
  POST /report/upload
  POST /report/embed
  POST /report/generate-tables

Logic:
  1. Attempt to process all files in the folder.
  2. Identify files that failed at any step.
  3. Automatically re-run ONLY the failed files.
  4. Repeat until all are successful or MAX_GLOBAL_ROUNDS is reached.

Usage:
  python mass_upload_via_api.py           # real run
  python mass_upload_via_api.py --dry-run  # only list files
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

# Stop looping after this many attempts to prevent infinite loops on bad files
MAX_GLOBAL_ROUNDS = 10

# Headers
HEADERS = {"access-token": API_KEY}

# Request timeout (15 minutes per request to handle large files)
REQUEST_TIMEOUT = 900

# Per-call retry settings (network blips)
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0 
BACKOFF_MULTIPLIER = 2.0

# Delay between files
PER_FILE_DELAY = 0.5

# Endpoints
UPLOAD_ENDPOINT = f"{API_BASE_URL}/report/upload"
EMBED_ENDPOINT = f"{API_BASE_URL}/report/embed"
TABLES_ENDPOINT = f"{API_BASE_URL}/report/generate-tables"

# ---------- helpers ----------
def retry_post(url: str, files=None, data=None, json_payload=None, headers=None, max_retries=MAX_RETRIES) -> Optional[requests.Response]:
    attempt = 0
    backoff = INITIAL_BACKOFF
    while attempt < max_retries:
        try:
            attempt += 1
            resp = requests.post(url, headers=headers or HEADERS, files=files, data=data, json=json_payload, timeout=REQUEST_TIMEOUT)
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
    print(f" -> upload: {file_path.name}")
    with open(file_path, "rb") as fh:
        files = {"file": (file_path.name, fh, "application/pdf")}
        resp = retry_post(UPLOAD_ENDPOINT, files=files)
    if resp is None:
        return False, {"error": "no_response"}
    if resp.status_code >= 500:
        return False, {"error": f"server_error_{resp.status_code}", "text": resp.text}
    data = safe_json(resp)
    if not data or data.get("error", True):
        return False, {"error": "backend_error_or_malformed", "status_code": resp.status_code, "body": resp.text, "json": data}
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
    if resp.status_code != 200 or data is None or data.get("error", True):
        return False, {"error": "embed_failed", "status_code": resp.status_code, "body": resp.text, "json": data}
    return True, data.get("data", {})

def call_generate_tables(chatid: str, gu_id: str) -> Tuple[bool, Dict]:
    print(f" -> generate-tables: chatid={chatid}, gu_id={gu_id}")
    payload = {"chatid": chatid, "gu_id": gu_id}
    resp = retry_post(TABLES_ENDPOINT, data=payload)
    if resp is None:
        return False, {"error": "no_response"}
    if resp.status_code == 208:
        return True, {"status": "already_generated"}
    if resp.status_code != 200:
        return False, {"error": f"tables_failed_status_{resp.status_code}", "body": resp.text}
    data = safe_json(resp)
    if data is None or data.get("error", True):
        return False, {"error": "tables_backend_error", "body": resp.text, "json": data}
    return True, data.get("data", {})

def write_results_to_csv(results_dict):
    """Writes the current state of all files to CSV."""
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "file", "status", "upload_ok", "upload_info", "embed_ok", "embed_info", "tables_ok", "tables_info"
        ])
        writer.writeheader()
        for filename in sorted(results_dict.keys()):
            r = results_dict[filename]
            # Create a copy so we don't modify the running state
            r_out = r.copy()
            
            # --- FIX IS HERE: Remove the internal '_path' key ---
            if "_path" in r_out:
                del r_out["_path"]
            # ----------------------------------------------------

            for k in ["upload_info", "embed_info", "tables_info"]:
                v = r_out.get(k)
                if isinstance(v, dict):
                    r_out[k] = str(v)
                else:
                    r_out[k] = v
            writer.writerow(r_out)

# ---------- main logic ----------
def process_all_files(dry_run: bool = False):
    # 1. Identify all PDF files
    all_pdfs = sorted(list(PDF_FOLDER.glob("*.pdf")))
    if not all_pdfs:
        print(f"[INFO] No PDF files found in {PDF_FOLDER}")
        return

    print(f"[INFO] Found {len(all_pdfs)} total files.")
    
    # Master dictionary to track the state of every file
    master_results = {}

    # Initialize master results
    for pdf in all_pdfs:
        master_results[pdf.name] = {
            "file": pdf.name,
            "status": "pending",
            "upload_ok": False, "upload_info": None,
            "embed_ok": False, "embed_info": None,
            "tables_ok": False, "tables_info": None,
            "_path": pdf
        }

    files_to_process = [p.name for p in all_pdfs]
    current_round = 1

    # --- GLOBAL RETRY LOOP ---
    while files_to_process and current_round <= MAX_GLOBAL_ROUNDS:
        print(f"\n{'='*60}")
        print(f"STARTING ROUND {current_round} / {MAX_GLOBAL_ROUNDS}")
        print(f"Files to process: {len(files_to_process)}")
        print(f"{'='*60}\n")

        failed_in_this_round = []

        for i, filename in enumerate(files_to_process):
            row = master_results[filename]
            pdf_path = row["_path"]
            
            print(f"[{current_round}/{i+1}] Processing: {filename}")
            
            # --- TIMER START ---
            file_start_time = time.time() 

            if dry_run:
                print(f"[DRY] Would processed {filename}")
                row["status"] = "dry_run"
                continue

            # --- Step 1: Upload ---
            if not row["upload_ok"]:
                upload_ok, upload_data = call_upload(pdf_path)
                row["upload_ok"] = bool(upload_ok)
                row["upload_info"] = upload_data
                if not upload_ok:
                    print(f"[ERROR] Upload failed: {upload_data}")
                    row["status"] = "failed_upload"
                    failed_in_this_round.append(filename)
                    time.sleep(PER_FILE_DELAY)
                    continue
            
            u_info = row["upload_info"]
            chatid = u_info.get("chatid") or u_info.get("chat_id")
            gu_id = u_info.get("gu_id") or u_info.get("file_id")

            if not chatid or not gu_id:
                print(f"[ERROR] Missing IDs in upload response: {u_info}")
                row["status"] = "failed_ids"
                failed_in_this_round.append(filename)
                continue

            # --- Step 2: Embed ---
            if not row["embed_ok"]:
                embed_ok, embed_data = call_embed(chatid=chatid, gu_id=gu_id)
                row["embed_ok"] = bool(embed_ok)
                row["embed_info"] = embed_data
                if not embed_ok:
                    print(f"[ERROR] Embed failed: {embed_data}")
                    row["status"] = "failed_embed"
                    failed_in_this_round.append(filename)
                    time.sleep(PER_FILE_DELAY)
                    continue

            # --- Step 3: Generate Tables ---
            if not row["tables_ok"]:
                tables_ok, tables_data = call_generate_tables(chatid=chatid, gu_id=gu_id)
                row["tables_ok"] = bool(tables_ok)
                row["tables_info"] = tables_data
                if not tables_ok:
                    print(f"[ERROR] Tables failed: {tables_data}")
                    row["status"] = "failed_tables"
                    failed_in_this_round.append(filename)
                    continue

            # --- TIMER END ---
            elapsed = time.time() - file_start_time
            
            # Update status and print time
            row["status"] = "success"
            print(f"[OK] Successfully processed {filename} in {elapsed:.2f} seconds")
            
            write_results_to_csv(master_results)
            time.sleep(PER_FILE_DELAY)

        files_to_process = failed_in_this_round
        current_round += 1
        write_results_to_csv(master_results)

    # --- SUMMARY ---
    print(f"\n{'='*60}")
    print("PROCESSING COMPLETE")
    success_count = sum(1 for r in master_results.values() if r["status"] == "success")
    fail_count = len(master_results) - success_count
    print(f"Total Files: {len(master_results)}")
    print(f"Successful : {success_count}")
    print(f"Failed     : {fail_count}")
    
    if fail_count > 0:
        print("\nFailed Files:")
        for fname, res in master_results.items():
            if res["status"] != "success":
                print(f" - {fname} ({res['status']})")
    
    print(f"\nFull results saved to: {OUTPUT_CSV}")

# ---------- entry ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mass upload PDFs with auto-retry logic")
    parser.add_argument("--dry-run", action="store_true", help="Only list files")
    args = parser.parse_args()
    
    process_all_files(dry_run=args.dry_run)