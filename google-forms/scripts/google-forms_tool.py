#!/usr/bin/env python3
"""
google-forms_tool.py - Official Google Forms API v1 CLI for Aina

Provides seamless Google Forms operations for Aina:
- Uses existing Google OAuth credentials managed by gdrive_tool.
- Healthcheck & status inspection (checks whether Google Forms API is enabled in GCP).
- Create new Google Forms with custom title and description.
- Add questions (Text, Paragraph, Multiple Choice, Checkbox, Dropdown, Scale, Date).
- Retrieve form structure, responder URI, and edit URI.
- Fetch and summarize responses.
"""

import argparse
import json
import os
import sys
import time
import urllib.parse

# Add paths to load gdrive_tool
for p in [
    "/app/skills/gdrive/scripts",
    "/app/workspaces/default/.agents/skills/gdrive/scripts",
    ".agents/skills/gdrive/scripts",
    "skills/gdrive/scripts",
    "/root/projects/aina/skills/gdrive/scripts"
]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.append(p)

try:
    import gdrive_tool
except ImportError:
    gdrive_tool = None

import requests

FORMS_API_BASE = "https://forms.googleapis.com/v1/forms"
DEFAULT_TIMEOUT = 30


def get_token():
    """Retrieve valid OAuth access token from gdrive_tool or environment."""
    env_token = os.environ.get("GOOGLE_ACCESS_TOKEN", "").strip()
    if env_token:
        return env_token

    if gdrive_tool:
        try:
            return gdrive_tool.get_valid_access_token()
        except Exception as e:
            raise RuntimeError(f"Gagal mengambil token Google via gdrive_tool: {e}")

    # Fallback: check /app/data/google_token.json directly
    token_file = "/app/data/google_token.json"
    if os.path.exists(token_file):
        with open(token_file, "r", encoding="utf-8") as f:
            tdata = json.load(f)
            return tdata.get("access_token")

    raise RuntimeError("Kredensial Google OAuth belum ditemukan.")


def check_api_status():
    """Verify if Google Forms API is enabled and accessible."""
    try:
        token = get_token()
    except Exception as e:
        return {
            "status": "unauthenticated",
            "error": str(e),
            "advice": "Jalankan 'gdrive_tool auth' untuk login ke akun Google."
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test dummy form creation or ping endpoint
    # Forms API returns 403 SERVICE_DISABLED if not enabled in GCP project
    test_body = {"info": {"title": "Ping Check"}}
    try:
        resp = requests.post(FORMS_API_BASE, headers=headers, json=test_body, timeout=DEFAULT_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            # Clean up the test form if created
            form_id = data.get("formId")
            return {
                "status": "ready",
                "api_enabled": True,
                "message": "Google Forms API aktif dan dapat diakses normal.",
                "test_form_id": form_id
            }
        elif resp.status_code == 403:
            err = resp.json().get("error", {})
            msg = err.get("message", "")
            activation_url = "https://console.developers.google.com/apis/api/forms.googleapis.com/overview?project=169071183041"
            for detail in err.get("details", []):
                for link in detail.get("links", []):
                    if "activation" in link.get("description", "").lower() or "google developers console" in link.get("description", "").lower():
                        activation_url = link.get("url", activation_url)

            return {
                "status": "disabled",
                "api_enabled": False,
                "http_code": 403,
                "reason": "SERVICE_DISABLED",
                "message": msg,
                "activation_url": activation_url,
                "advice": f"Aktifkan Google Forms API di Google Cloud Console: {activation_url}"
            }
        else:
            return {
                "status": "error",
                "http_code": resp.status_code,
                "response": resp.text
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def cmd_status(args):
    result = check_api_status()
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_create(args):
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    info = {
        "title": args.title,
    }
    if args.document_title:
        info["documentTitle"] = args.document_title
    else:
        info["documentTitle"] = args.title

    if args.desc:
        info["description"] = args.desc

    payload = {"info": info}

    resp = requests.post(FORMS_API_BASE, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
    if resp.status_code != 200:
        print(json.dumps({
            "status": "error",
            "http_code": resp.status_code,
            "response": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        }, indent=2), file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    form_id = data.get("formId")
    responder_uri = data.get("responderUri")
    edit_uri = f"https://docs.google.com/forms/d/{form_id}/edit"

    out = {
        "status": "success",
        "form_id": form_id,
        "title": args.title,
        "responder_url": responder_uri,
        "edit_url": edit_uri,
        "raw": data
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


def cmd_get(args):
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{FORMS_API_BASE}/{args.form_id}"

    resp = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
    if resp.status_code != 200:
        print(json.dumps({
            "status": "error",
            "http_code": resp.status_code,
            "response": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        }, indent=2), file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    form_id = data.get("formId")
    edit_uri = f"https://docs.google.com/forms/d/{form_id}/edit"
    data["edit_url"] = edit_uri

    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_add_questions(args):
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Load questions schema from JSON string or file
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            q_list = json.load(f)
    elif args.json:
        q_list = json.loads(args.json)
    else:
        print(json.dumps({"status": "error", "message": "Harus menyertakan --file atau --json"}, indent=2), file=sys.stderr)
        sys.exit(1)

    if not isinstance(q_list, list):
        if isinstance(q_list, dict) and "questions" in q_list:
            q_list = q_list["questions"]
        elif isinstance(q_list, dict) and "requests" in q_list:
            # Direct batchUpdate payload
            requests_payload = q_list["requests"]
            payload = {"requests": requests_payload}
            url = f"{FORMS_API_BASE}/{args.form_id}:batchUpdate"
            resp = requests.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
            print(resp.text)
            return

    # Convert high-level questions into Forms API createItem requests
    requests_payload = []
    for idx, q in enumerate(q_list):
        title = q.get("title", f"Pertanyaan {idx+1}")
        desc = q.get("description", "")
        required = q.get("required", False)
        q_type = q.get("type", "text").lower()

        question_obj = {"required": required}

        if q_type in ["text", "short_text", "short"]:
            question_obj["textQuestion"] = {"paragraph": False}
        elif q_type in ["paragraph", "long_text", "textarea"]:
            question_obj["textQuestion"] = {"paragraph": True}
        elif q_type in ["radio", "choice", "multiple_choice"]:
            options = [{"value": opt} for opt in q.get("options", [])]
            question_obj["choiceQuestion"] = {
                "type": "RADIO",
                "options": options,
                "shuffle": q.get("shuffle", False)
            }
        elif q_type in ["checkbox", "checkboxes"]:
            options = [{"value": opt} for opt in q.get("options", [])]
            question_obj["choiceQuestion"] = {
                "type": "CHECKBOX",
                "options": options
            }
        elif q_type in ["dropdown", "select"]:
            options = [{"value": opt} for opt in q.get("options", [])]
            question_obj["choiceQuestion"] = {
                "type": "DROP_DOWN",
                "options": options
            }
        elif q_type in ["scale", "linear_scale"]:
            low = q.get("low", 1)
            high = q.get("high", 5)
            question_obj["scaleQuestion"] = {
                "low": low,
                "high": high,
                "lowLabel": q.get("low_label", ""),
                "highLabel": q.get("high_label", "")
            }
        elif q_type == "date":
            question_obj["dateQuestion"] = {
                "includeTime": q.get("include_time", False),
                "includeYear": q.get("include_year", True)
            }
        elif q_type == "time":
            question_obj["timeQuestion"] = {
                "duration": q.get("duration", False)
            }
        else:
            question_obj["textQuestion"] = {"paragraph": False}

        item_dict = {
            "title": title,
            "questionItem": {
                "question": question_obj
            }
        }
        if desc:
            item_dict["description"] = desc

        requests_payload.append({
            "createItem": {
                "item": item_dict,
                "location": {
                    "index": idx
                }
            }
        })

    payload = {"requests": requests_payload}
    url = f"{FORMS_API_BASE}/{args.form_id}:batchUpdate"
    resp = requests.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)

    if resp.status_code != 200:
        print(json.dumps({
            "status": "error",
            "http_code": resp.status_code,
            "response": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        }, indent=2), file=sys.stderr)
        sys.exit(1)

    print(json.dumps({
        "status": "success",
        "form_id": args.form_id,
        "questions_added": len(requests_payload),
        "details": resp.json()
    }, indent=2, ensure_ascii=False))


def cmd_responses(args):
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{FORMS_API_BASE}/{args.form_id}/responses"

    resp = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
    if resp.status_code != 200:
        print(json.dumps({
            "status": "error",
            "http_code": resp.status_code,
            "response": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        }, indent=2), file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    responses = data.get("responses", [])
    print(json.dumps({
        "status": "success",
        "form_id": args.form_id,
        "total_responses": len(responses),
        "responses": responses
    }, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Google Forms API v1 Management Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Periksa kesiapan koneksi dan aktivasi Google Forms API di GCP")
    p_status.set_defaults(func=cmd_status)

    # create
    p_create = subparsers.add_parser("create", help="Buat Google Form baru")
    p_create.add_argument("--title", required=True, help="Judul form")
    p_create.add_argument("--desc", help="Deskripsi form")
    p_create.add_argument("--document-title", help="Judul dokumen file di Google Drive")
    p_create.set_defaults(func=cmd_create)

    # get
    p_get = subparsers.add_parser("get", help="Ambil struktur dan rincian form")
    p_get.add_argument("--form-id", required=True, help="ID Google Form")
    p_get.set_defaults(func=cmd_get)

    # add-questions
    p_add = subparsers.add_parser("add-questions", help="Tambah pertanyaan ke form")
    p_add.add_argument("--form-id", required=True, help="ID Google Form")
    p_add.add_argument("--file", help="Path ke file JSON daftar pertanyaan")
    p_add.add_argument("--json", help="String JSON daftar pertanyaan")
    p_add.set_defaults(func=cmd_add_questions)

    # responses
    p_resp = subparsers.add_parser("responses", help="Ambil respon atau jawaban yang masuk")
    p_resp.add_argument("--form-id", required=True, help="ID Google Form")
    p_resp.set_defaults(func=cmd_responses)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
