import re
import csv
import io
import base64
from flask import Flask, request, render_template_string, redirect, url_for

# terraform_checker.py
#
# Simple Flask web app to upload a Terraform (.tf) file, scan for common security issues,
# display results in a table on screen, and provide a CSV report for download.
#
# Usage:
# 1. Install dependencies: pip install flask
# 2. Run: python terraform_checker.py
# 3. Open http://127.0.0.1:5000 in your browser and upload a .tf file.
#
# Notes:
# - This scanner uses heuristic / regex rules to find common risky patterns (public access,
#   hardcoded credentials, overly broad IAM, etc.). It is not a substitute for full static
#   analysis tools but provides quick feedback and a severity score (1-10).
# - The CSV download is provided as a data-URI link (no server-side temp files).
#
# Author: GitHub Copilot
# Wrap Flask's render_template_string to rewrite enumerate-style loops to use Jinja2 loop counters
_orig_render_template_string = render_template_string
def render_template_string(source, *args, **kwargs):
    if isinstance(source, str):
        source = source.replace("{% for i, it in enumerate(issues, start=1) %}", "{% for it in issues %}")
        source = source.replace("{{ i }}", "{{ loop.index }}")
    return _orig_render_template_string(source, *args, **kwargs)

app = Flask(__name__)

# Define detection rules (id, description, pattern-or-function, severity)
# pattern can be a compiled regex (applied file-wide) or a function(content) -> list of matches
RULES = [
    {
        "id": "HARD_CODED_AWS_ACCESS_KEY",
        "description": "Hardcoded AWS access key (AKIA...)",
        "pattern": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "severity": 10,
    },
    {
        "id": "HARD_CODED_AWS_SECRET",
        "description": "Hardcoded AWS secret key or aws_secret_access_key assignment",
        "pattern": re.compile(
            r"aws_secret_access_key\s*=\s*['\"].+?['\"]|aws_secret_access_key\s*:\s*['\"].+?['\"]",
            re.IGNORECASE,
        ),
        "severity": 10,
    },
    {
        "id": "OPEN_CIDR_0_0_0_0",
        "description": "Open CIDR 0.0.0.0/0 detected (potentially public access)",
        "pattern": re.compile(r"0\.0\.0\.0/0"),
        "severity": 9,
    },
    {
        "id": "SSH_OPEN_TO_WORLD",
        "description": "SSH (port 22) open to 0.0.0.0/0",
        "pattern": "ssh_open_to_world",  # special handler
        "severity": 10,
    },
    {
        "id": "RDP_OPEN_TO_WORLD",
        "description": "RDP (port 3389) open to 0.0.0.0/0",
        "pattern": "rdp_open_to_world",  # special handler
        "severity": 10,
    },
    {
        "id": "S3_PUBLIC_ACL",
        "description": "S3 bucket public ACL or public flag (public-read, public-read-write, public = true)",
        "pattern": re.compile(r"(?i)\b(public-read|public-read-write)\b|\bacl\s*=\s*['\"]?(public-read|public-read-write)['\"]?|\bpublic\s*=\s*true\b"),
        "severity": 9,
    },
    {
        "id": "RDS_PUBLICLY_ACCESSIBLE",
        "description": "RDS instance marked publicly_accessible = true",
        "pattern": re.compile(r"(?i)publicly_accessible\s*=\s*true"),
        "severity": 8,
    },
    {
        "id": "IAM_POLICY_WILDCARD",
        "description": "IAM policy contains wildcard Action or Resource ('*')",
        "pattern": re.compile(r"(?s)(\"Action\"\s*:\s*\"?\*\"?|Action\s*=\s*['\"]\*['\"]|\"Resource\"\s*:\s*\"?\*\"?|Resource\s*=\s*['\"]\*['\"])"),
        "severity": 10,
    },
    {
        "id": "UNENCRYPTED_EBS",
        "description": "Unencrypted EBS volume (encrypted = false)",
        "pattern": re.compile(r"(?i)encrypted\s*=\s*false"),
        "severity": 7,
    },
    {
        "id": "PROVISIONER_REMOTE_LOCAL_EXEC",
        "description": "Use of provisioner remote-exec/local-exec (may run arbitrary code)",
        "pattern": re.compile(r"(?i)provisioner\s+\"?(remote-exec|local-exec)\"?"),
        "severity": 5,
    },
]

def find_line_number(content: str, pos: int) -> int:
    return content.count("\n", 0, pos) + 1

def search_special_handlers(content: str):
    """
    Handle complex detections that need context, like SSH/RDP open to 0.0.0.0/0.
    Return list of match dicts similar to regex matches.
    """
    matches = []
    # Find all occurrences of 0.0.0.0/0 and check nearby context for port numbers or from_port/to_port keys
    for m in re.finditer(r"0\.0\.0\.0/0", content):
        start = max(m.start() - 200, 0)
        end = min(m.end() + 200, len(content))
        window = content[start:end]
        # Search for explicit port numbers in the window
        # Look for from_port or port or to_port assignments/numbers
        port_match = re.search(r"(from_port|to_port|port)\s*=\s*([0-9]+)", window, flags=re.IGNORECASE)
        if port_match:
            port = int(port_match.group(2))
            if port == 22:
                matches.append({"rule": "SSH_OPEN_TO_WORLD", "pos": m.start(), "snippet": window})
            elif port == 3389:
                matches.append({"rule": "RDP_OPEN_TO_WORLD", "pos": m.start(), "snippet": window})
            else:
                # generic open CIDR already handled by OPEN_CIDR_0_0_0_0 rule; we don't duplicate here
                pass
        else:
            # Also check for common port mentions (22 or 3389) even if not in from_port= form
            if re.search(r"\b22\b", window):
                matches.append({"rule": "SSH_OPEN_TO_WORLD", "pos": m.start(), "snippet": window})
            if re.search(r"\b3389\b", window):
                matches.append({"rule": "RDP_OPEN_TO_WORLD", "pos": m.start(), "snippet": window})
    return matches

def scan_content(content: str, filename: str):
    """
    Scan content of a Terraform file and return list of issue dicts:
    { filename, rule_id, description, severity, line, snippet }
    """
    issues = []
    # Apply regex-based rules
    for rule in RULES:
        pat = rule["pattern"]
        if isinstance(pat, re.Pattern):
            for m in pat.finditer(content):
                line = find_line_number(content, m.start())
                snippet = content[max(0, m.start()-80):min(len(content), m.end()+80)].strip()
                issues.append({
                    "filename": filename,
                    "rule_id": rule["id"],
                    "description": rule["description"],
                    "severity": rule["severity"],
                    "line": line,
                    "snippet": snippet.replace("\n", "\\n"),
                })
        else:
            # special handler names handled below
            pass

    # Special handlers (custom logic)
    special = search_special_handlers(content)
    for s in special:
        if s["rule"] == "SSH_OPEN_TO_WORLD":
            line = find_line_number(content, s["pos"])
            issues.append({
                "filename": filename,
                "rule_id": "SSH_OPEN_TO_WORLD",
                "description": "SSH (port 22) accessible from 0.0.0.0/0 (open to the world)",
                "severity": 10,
                "line": line,
                "snippet": s["snippet"].replace("\n", "\\n"),
            })
        elif s["rule"] == "RDP_OPEN_TO_WORLD":
            line = find_line_number(content, s["pos"])
            issues.append({
                "filename": filename,
                "rule_id": "RDP_OPEN_TO_WORLD",
                "description": "RDP (port 3389) accessible from 0.0.0.0/0 (open to the world)",
                "severity": 10,
                "line": line,
                "snippet": s["snippet"].replace("\n", "\\n"),
            })

    # Deduplicate similar findings by rule_id and line/snippet to avoid noisy duplicates
    seen = set()
    deduped = []
    for it in issues:
        key = (it["rule_id"], it["line"], it["snippet"])
        if key not in seen:
            seen.add(key)
            deduped.append(it)
    # Sort by severity desc then line
    deduped.sort(key=lambda x: (-x["severity"], x["line"]))
    return deduped

def issues_to_csv_bytes(issues):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["filename", "rule_id", "description", "severity", "line", "snippet"])
    for it in issues:
        writer.writerow([it["filename"], it["rule_id"], it["description"], it["severity"], it["line"], it["snippet"]])
    return output.getvalue().encode("utf-8")

INDEX_HTML = """
<!doctype html>
<title>Terraform Security Checker</title>
<h2>Terraform Security Checker</h2>
<form method=post enctype=multipart/form-data action="{{ url_for('scan') }}">
  <label>Upload a .tf file: <input type=file name=tf_file accept=".tf"></label>
  <input type=submit value="Scan">
</form>
<p>Rules applied: {{ rules_count }} heuristic checks. This is a simple scanner using regex/context heuristics.</p>
"""

RESULT_HTML = """
<!doctype html>
<title>Scan Results</title>
<h2>Scan Results for {{ filename }}</h2>
<p>Detected {{ issues|length }} potential issue(s).</p>
{% if download_link %}
<p><a href="{{ download_link }}" download="{{ filename }}_tfscan.csv">Download CSV report</a></p>
{% endif %}
<table border="1" cellpadding="6" cellspacing="0">
  <thead>
    <tr>
      <th>#</th>
      <th>Rule ID</th>
      <th>Description</th>
      <th>Severity (1-10)</th>
      <th>Line</th>
      <th>Snippet</th>
    </tr>
  </thead>
  <tbody>
  {% for i, it in enumerate(issues, start=1) %}
    <tr>
      <td>{{ i }}</td>
      <td>{{ it.rule_id }}</td>
      <td>{{ it.description }}</td>
      <td>{{ it.severity }}</td>
      <td>{{ it.line }}</td>
      <td style="font-family:monospace; white-space:pre-wrap;">{{ it.snippet }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
<p><a href="{{ url_for('index') }}">Scan another file</a></p>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML, rules_count=len(RULES))

@app.route("/scan", methods=["POST"])
def scan():
    uploaded = request.files.get("tf_file")
    if not uploaded or uploaded.filename == "":
        return redirect(url_for("index"))
    filename = uploaded.filename
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
    except Exception:
        # Fallback: treat as binary -> no matches
        content = ""
    issues = scan_content(content, filename)
    csv_bytes = issues_to_csv_bytes(issues)
    b64 = base64.b64encode(csv_bytes).decode("ascii")
    data_uri = f"data:text/csv;base64,{b64}"
    return render_template_string(RESULT_HTML, filename=filename, issues=issues, download_link=data_uri)

if __name__ == "__main__":
    # Run local dev server
    app.run(debug=True, port=5000)

# Prompts and context (kept in a comment for future reference)
# ----------------------------------------------------------------------
# 1) <currentDocument>
# I am in an empty file `/C:/Users/derri/Desktop/AI Class folder/AI_assisted/terraform_checker.py`.
# </currentDocument>
#
# 2) <userPrompt>
# I would like a program written in python that checks a terraform code for possible security issues it the code, i would like a way to upload a .tf file and for the app to scan it and give me a CSV repoort as well a a teble on srcreen also add a value to each item 10 being vert serious and 1 beiing a minor consern. in a comment keep this and any promts provided when creating example if i make changes later this prompt and the following ones will be listed in a list in side a comment af the end of the code
# </userPrompt>
#
# You can add more prompts below as you iterate; they will be preserved here.
# ----------------------------------------------------------------------