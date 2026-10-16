import os
import re
import io
import json
import base64
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

import requests
import streamlit as st
from groq import Groq
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Preformatted,
    PageBreak, KeepTogether
)

# ============================================================
# APP CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="RepoRiot | GitHub Project Lab",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

GITHUB_API = "https://api.github.com"
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MAX_FILE_BYTES = 180_000
MAX_REPO_FILES = 45
MAX_CONTEXT_CHARS = 10_000
REQUEST_TIMEOUT = 25

TEXT_EXTENSIONS = {
    ".py", ".ipynb", ".sql", ".md", ".txt", ".csv", ".tsv",
    ".json", ".jsonl", ".yaml", ".yml", ".xml", ".html", ".css",
    ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".h",
    ".hpp", ".r", ".R", ".ipynb", ".sh", ".bat", ".ps1",
    ".toml", ".ini", ".cfg", ".env.example", ".gitignore",
    ".dockerfile", ".prisma", ".go", ".rs", ".php",
}

SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__",
    "dist", "build", ".next", ".idea", ".vscode",
}

# ============================================================
# RETRO NEO-POP THEME
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

:root {
    --ink: #f7f3ff;
    --muted: #b9b1d0;
    --bg: #100b20;
    --panel: #1d1535;
    --panel2: #271b43;
    --pink: #ff4fa3;
    --lime: #d8ff3e;
    --cyan: #48e5ff;
    --orange: #ffb454;
}

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}
.stApp {
    background:
        radial-gradient(ellipse at 5% 0%, #402052 0%, transparent 35%),
        radial-gradient(ellipse at 100% 10%, #18364a 0%, transparent 28%),
        var(--bg);
    color: var(--ink);
}
[data-testid="stHeader"] {
    background: rgba(16,11,32,.86);
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1b1231, #110c21);
    border-right: 1px solid #46345f;
}
h1, h2, h3 {
    color: var(--ink) !important;
    letter-spacing: -0.035em;
}
p, li, label, .stMarkdown {
    color: var(--ink);
}
.hero {
    border: 2px solid var(--pink);
    border-radius: 24px;
    padding: 30px 32px;
    background: linear-gradient(120deg, #2b1748 0%, #1b183c 60%, #103242 100%);
    box-shadow: 7px 7px 0 var(--pink);
    margin: 8px 0 28px 0;
}
.eyebrow {
    color: var(--lime);
    font-family: 'Space Mono', monospace;
    text-transform: uppercase;
    letter-spacing: .14em;
    font-size: .78rem;
    font-weight: 700;
}
.hero h1 {
    font-size: clamp(2.2rem, 5vw, 4rem);
    line-height: 1.02;
    margin: 10px 0;
}
.hero p {
    color: #ddd5f1;
    max-width: 800px;
    font-size: 1.08rem;
}
.neo-card {
    background: var(--panel);
    border: 1px solid #55416f;
    border-radius: 18px;
    padding: 20px;
    margin: 10px 0;
}
.neo-card-pink {
    border: 1.5px solid var(--pink);
    box-shadow: 4px 4px 0 #702c62;
}
.neo-card-lime {
    border: 1.5px solid var(--lime);
    box-shadow: 4px 4px 0 #536021;
}
.neo-card-cyan {
    border: 1.5px solid var(--cyan);
    box-shadow: 4px 4px 0 #235a68;
}
.pill {
    display: inline-block;
    padding: 5px 10px;
    margin: 3px 5px 3px 0;
    border-radius: 999px;
    background: #34264d;
    border: 1px solid #665080;
    color: #f7f3ff;
    font-family: 'Space Mono', monospace;
    font-size: .76rem;
}
.mono {
    font-family: 'Space Mono', monospace;
    color: var(--lime);
}
div.stButton > button, div.stDownloadButton > button {
    border: 1.5px solid var(--lime);
    border-radius: 12px;
    background: var(--lime);
    color: #171024;
    font-weight: 800;
    min-height: 2.8rem;
    transition: transform .12s ease, box-shadow .12s ease;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    transform: translate(-2px, -2px);
    box-shadow: 4px 4px 0 var(--pink);
    border-color: var(--pink);
    color: #171024;
}
div.stButton > button[kind="secondary"] {
    background: #2a2043;
    color: var(--ink);
    border-color: #755a91;
}
div[data-testid="stTextInput"] input {
    background: #1c1431;
    color: white;
    border: 1.5px solid #73558e;
    border-radius: 12px;
}
div[data-testid="stSelectbox"] > div > div {
    background: #1c1431;
    border-radius: 10px;
}
[data-testid="stMetric"] {
    background: #211738;
    border: 1px solid #49365f;
    border-radius: 14px;
    padding: 14px;
}
[data-testid="stMetricLabel"] {
    color: #c8bbdf !important;
}
[data-testid="stMetricValue"] {
    color: var(--lime) !important;
}
hr {
    border-color: #49365f;
}
div[data-testid="stExpander"] {
    border: 1px solid #49365f;
    border-radius: 12px;
    background: #1a1230;
}
.stAlert {
    border-radius: 12px;
}
footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPERS: SESSION STATE AND API CLIENT
# ============================================================

def init_state():
    defaults = {
        "repo_url": "",
        "repo": None,
        "files": {},
        "tree": [],
        "readme": "",
        "selected_file": None,
        "explanations": {},
        "quizzes": {},
        "answers": {},
        "submitted": {},
        "interview_qa": None,
        "page": "Home",
        "repo_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_client():
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        st.error(
            "Groq API key was not passed to this Streamlit process. "
            "Stop the app and relaunch it using the Jupyter launch cell below."
        )
        st.code(
            "from getpass import getpass\n"
            "import os, subprocess, sys\n"
            "key = getpass('Enter Groq API key: ')\n"
            "env = os.environ.copy()\n"
            "env['GROQ_API_KEY'] = key\n"
            "subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', "
            "'github_project_lab.py', '--server.port', '8501'], env=env)"
        )
        st.stop()
    return Groq(api_key=key)


def ask_ai(prompt, system="You are a precise, practical software engineering tutor.",
           max_tokens=4500, temperature=0.2):
    client = get_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def extract_json(text):
    """Parse JSON even if the model surrounds it with Markdown fences."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise ValueError("The AI response did not contain valid JSON.")


# ============================================================
# GITHUB REPOSITORY FUNCTIONS
# ============================================================

def parse_github_url(url):
    url = url.strip().rstrip("/")
    url = re.sub(r"\.git$", "", url)
    match = re.match(
        r"^(?:https?://)?(?:www\.)?github\.com/([^/\s]+)/([^/\s]+)(?:/.*)?$",
        url,
        re.I,
    )
    if not match:
        raise ValueError(
            "Enter a GitHub repository URL like "
            "https://github.com/owner/repository"
        )
    owner, repo = match.group(1), match.group(2)
    if owner in {"settings", "features", "topics", "orgs", "marketplace"}:
        raise ValueError("That looks like a GitHub page, not a repository URL.")
    return owner, repo


def github_get(path, params=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "RepoRiot-GitHub-Project-Lab",
    }
    # Optional token can improve GitHub API rate limits.
    # Public repositories work without one.
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(
        f"{GITHUB_API}{path}",
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code == 404:
        raise ValueError(
            "Repository or file not found. Check the URL and confirm "
            "that the repository is public."
        )
    if response.status_code == 403:
        raise ValueError(
            "GitHub API rate limit reached. Wait a little and try again, "
            "or optionally configure a GitHub token in the notebook environment."
        )
    response.raise_for_status()
    return response.json()


def is_text_file(path):
    p = Path(path)
    name = p.name.lower()
    if any(part.lower() in SKIP_DIRS for part in p.parts):
        return False
    if name in {"dockerfile", "makefile", "license", "readme"}:
        return True
    return p.suffix.lower() in TEXT_EXTENSIONS


def load_repository(url):
    owner, repo_name = parse_github_url(url)
    base = f"/repos/{owner}/{repo_name}"
    metadata = github_get(base)

    branch = metadata.get("default_branch") or "main"
    tree_data = github_get(
        f"{base}/git/trees/{branch}",
        params={"recursive": "1"},
    )
    tree = tree_data.get("tree", [])

    # If the recursive tree is truncated, keep the available entries.
    tree = [
        item for item in tree
        if item.get("type") == "blob"
        and item.get("path")
        and is_text_file(item["path"])
        and item.get("size", 0) <= MAX_FILE_BYTES
    ][:MAX_REPO_FILES]

    files = {}
    readme = ""

    for item in tree:
        path = item["path"]
        try:
            content_data = github_get(f"{base}/contents/{path}")
            encoded = content_data.get("content", "")
            if content_data.get("encoding") == "base64":
                raw = base64.b64decode(encoded)
                content = raw.decode("utf-8", errors="replace")
            else:
                content = content_data.get("content", "")
            files[path] = content[:MAX_FILE_BYTES]
            if Path(path).name.lower().startswith("readme") and not readme:
                readme = content[:MAX_FILE_BYTES]
        except (requests.RequestException, ValueError, KeyError):
            # Skip individual files that cannot be fetched; keep other files.
            continue

    # If README was not in the tree, check the standard endpoint.
    if not readme:
        try:
            data = github_get(f"{base}/readme")
            if data.get("encoding") == "base64":
                readme = base64.b64decode(data["content"]).decode(
                    "utf-8", errors="replace"
                )
            if readme:
                files.setdefault(data.get("path", "README.md"), readme)
        except Exception:
            pass

    if not files:
        raise ValueError(
            "I couldn't retrieve readable files. The repository may be empty, "
            "private, or mostly contain unsupported/binary file types."
        )

    return {
        "metadata": metadata,
        "owner": owner,
        "name": repo_name,
        "branch": branch,
        "files": files,
        "readme": readme,
        "tree": tree,
        "tree_truncated": tree_data.get("truncated", False),
    }


def file_kind(path):
    suffix = Path(path).suffix.lower()
    name = Path(path).name.lower()
    if suffix == ".csv" or suffix == ".tsv":
        return "Dataset"
    if suffix == ".sql":
        return "SQL"
    if suffix == ".ipynb":
        return "Notebook"
    if suffix == ".py":
        return "Python"
    if name.startswith("readme"):
        return "README"
    if suffix in {".json", ".yaml", ".yml", ".toml"}:
        return "Configuration / data"
    return suffix.lstrip(".").upper() or "Text"


def make_repo_context(repo):
    chunks = []
    total = 0
    meta = repo["metadata"]
    chunks.append(
        f"REPOSITORY: {repo['owner']}/{repo['name']}\n"
        f"DESCRIPTION: {meta.get('description') or 'Not provided'}\n"
        f"LANGUAGES: {json.dumps(meta.get('language'))}\n"
        f"DEFAULT BRANCH: {repo['branch']}\n"
    )
    for path, content in repo["files"].items():
        piece = f"\n\n===== FILE: {path} =====\n{content[:5000]}"
        if total + len(piece) > MAX_CONTEXT_CHARS:
            break
        chunks.append(piece)
        total += len(piece)
    return "\n".join(chunks)


# ============================================================
# EXPLANATIONS, MCQ ASSESSMENTS, AND INTERVIEW QUESTIONS
# ============================================================

def explain_file(repo, path, content):
    kind = file_kind(path)
    prompt = f"""
Explain this repository file for a learner preparing for a technical interview.

Repository: {repo['owner']}/{repo['name']}
Repository description: {repo['metadata'].get('description') or 'Not supplied'}
File path: {path}
File type: {kind}

Requirements:
- Start with the purpose of this exact file.
- Explain the important sections and the order in which they work.
- Explain important variables, functions, classes, transformations, and dependencies.
- For SQL, explain each query, joins, filters, aggregations, CTEs, window functions,
  and the business question each query answers, if present.
- For CSV/TSV data, explain column names, likely data types, sample values,
  target/label columns only when supported by the data, and data-quality concerns.
  Do not claim that unseen rows or undocumented labels exist.
- For notebooks, explain markdown, code cells, data flow, and model steps.
- For README files, explain setup, usage, architecture, and claimed results.
- If code is long, explain it in logical blocks and include line numbers where feasible.
- Separate facts directly visible in the file from reasonable inferences.
- Mention limitations, potential bugs, and interview talking points.
- Use clear headings and practical examples. Do not invent project details.

FILE CONTENT:
```text
{content[:8000]}
```
"""
    return ask_ai(
        prompt,
        system="You are a meticulous senior engineer and patient technical interviewer.",
        max_tokens=5000,
    )


def generate_quiz(repo, path, content):
    prompt = f"""
Create exactly 10 multiple-choice assessment questions about the specific file below.
Questions must test actual understanding, not generic trivia.

Repository: {repo['owner']}/{repo['name']}
File: {path}
File type: {file_kind(path)}

For a dataset, test real columns, values, data types, labels only if evident,
and data-quality interpretation. For SQL, test the actual query logic, joins,
filters, grouping, aggregation, CTEs or window functions that appear.
For source code, test actual functions, variables, logic, libraries, and data flow.
For README/config files, test documented setup, architecture, and behavior.

Rules:
- Exactly 10 questions.
- Four options per question.
- Exactly one correct option.
- Explanations must be short and tied to the file.
- Never make up columns, functions, query behavior, or outputs.
- If information is not present in the file, don't ask about it.

Return ONLY valid JSON in this shape:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": ["A", "B", "C", "D"],
      "answer": 0,
      "explanation": "Short reason"
    }}
  ]
}}

FILE CONTENT:
```text
{content[:8000]}
```
"""
    data = extract_json(ask_ai(
        prompt,
        system="You create accurate file-specific assessments. Output valid JSON only.",
        max_tokens=3500,
        temperature=0.1,
    ))
    questions = data.get("questions", [])
    if len(questions) != 10:
        raise ValueError("The AI did not return exactly 10 questions. Please retry.")
    for q in questions:
        if len(q.get("options", [])) != 4 or q.get("answer") not in [0, 1, 2, 3]:
            raise ValueError("The generated quiz had an invalid question format.")
    return questions

def limit_repo_context(context, max_chars=5000):
    """Limit repository context before sending it to Groq."""
    if not context:
        return ""

    context = str(context).strip()

    if len(context) > max_chars:
        context = (
            context[:max_chars]
            + "\n\n[Repository context truncated.]"
        )

    return context

def generate_interview_qa(repo):
    context = limit_repo_context(make_repo_context(repo), max_chars=5000)
    prompt = f"""
Create 10 high-value technical interview questions and answers about the WHOLE
repository, using the repository context below.

Include a balanced selection covering:
- Project purpose and end-to-end workflow.
- Dataset source, columns, target/labels, and preprocessing only if supported.
- Important code files, functions, dependencies, and architecture.
- SQL business questions and actual query logic if SQL exists.
- Model/algorithm and evaluation metrics only if the repository supports them.
- Design decisions, limitations, validation, and possible improvements.

Answers must be concise: no more than 5 lines each. Use exact names and evidence
from the files wherever possible. If the repository doesn't provide an answer,
say "The repository does not specify this" rather than inventing details.
Do not create generic questions that ignore the project's actual content.
Return ONLY valid JSON:
{{
  "qa": [
    {{"question": "Question?", "answer": "Answer in at most 5 lines."}}
  ]
}}

Repository context:
{context}
"""
    data = extract_json(ask_ai(
        prompt,
        system="You are a senior technical interviewer. Be accurate, specific, and concise.",
        max_tokens=4000,
        temperature=0.15,
    ))
    qa = data.get("qa", [])
    if len(qa) != 10:
        raise ValueError("The AI did not return exactly 10 interview Q/A pairs.")
    return qa


# ============================================================


def make_limited_repo_context(repo, max_chars=10000):
    """Keep repository context small enough for Groq requests."""
    context = make_repo_context(repo)

    if not isinstance(context, str):
        context = str(context)

    if len(context) > max_chars:
        context = (
            context[:max_chars]
            + "\n\n[Repository context truncated to fit the AI request.]"
        )

    return context


# PDF EXPORT
# ============================================================

def create_pdf(title, body):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=title,
        author="RepoRiot GitHub Project Lab",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="NeoTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=22, leading=27, textColor=colors.HexColor("#5A267D"),
        alignment=TA_LEFT, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="NeoHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=14, leading=18, textColor=colors.HexColor("#A51D72"),
        spaceBefore=12, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="NeoBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9.5, leading=14, spaceAfter=7,
        textColor=colors.HexColor("#252033"),
    ))
    styles.add(ParagraphStyle(
        name="NeoCode", parent=styles["Code"], fontName="Courier",
        fontSize=7.5, leading=10, backColor=colors.HexColor("#F0ECF8"),
        borderPadding=6, spaceAfter=8,
    ))

    story = [Paragraph(escape(title), styles["NeoTitle"])]
    story.append(Paragraph(
        "Generated by RepoRiot — GitHub Project Lab",
        styles["NeoBody"],
    ))
    story.append(Spacer(1, 8))

    # Convert Markdown-like text into safe PDF paragraphs.
    in_code = False
    code_lines = []

    def flush_code():
        nonlocal code_lines
        if code_lines:
            story.append(Preformatted("\n".join(code_lines), styles["NeoCode"]))
            code_lines = []

    for line in body.splitlines():
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code:
                in_code = True
            else:
                in_code = False
                flush_code()
            continue

        if in_code:
            code_lines.append(line[:180])
            continue

        if not stripped:
            story.append(Spacer(1, 4))
        elif stripped.startswith("# "):
            story.append(Paragraph(escape(stripped[2:]), styles["NeoTitle"]))
        elif stripped.startswith("## ") or stripped.startswith("### "):
            story.append(Paragraph(escape(stripped.lstrip("# ")), styles["NeoHeading"]))
        elif stripped.startswith(("- ", "* ")):
            story.append(Paragraph(
                "&#8226; " + escape(stripped[2:]), styles["NeoBody"]
            ))
        elif re.match(r"^\d+[\.)]\s", stripped):
            story.append(Paragraph(escape(stripped), styles["NeoBody"]))
        else:
            safe = escape(stripped)
            safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
            safe = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", safe)
            story.append(Paragraph(safe, styles["NeoBody"]))

    flush_code()
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================
# REUSABLE UI
# ============================================================

def render_hero():
    st.markdown("""
    <div class="hero">
      <div class="eyebrow">✦ Learn the code. Own the interview. ✦</div>
      <h1>RepoRiot <span style="color:#d8ff3e">Project Lab</span></h1>
      <p>Your GitHub repository, turned into a hands-on learning studio.
      Explore files, understand the logic, test yourself, and get interview-ready.</p>
      <span class="pill">AI CODE EXPLAINER</span>
      <span class="pill">FILE-BY-FILE LEARNING</span>
      <span class="pill">MCQ ARCADE</span>
      <span class="pill">PDF EXPORTS</span>
    </div>
    """, unsafe_allow_html=True)


def render_repo_overview(repo):
    meta = repo["metadata"]
    files = repo["files"]
    python_count = sum(Path(p).suffix.lower() == ".py" for p in files)
    sql_count = sum(Path(p).suffix.lower() == ".sql" for p in files)
    dataset_count = sum(Path(p).suffix.lower() in {".csv", ".tsv"} for p in files)

    cols = st.columns(4)
    cols[0].metric("Readable files", len(files))
    cols[1].metric("Python files", python_count)
    cols[2].metric("SQL files", sql_count)
    cols[3].metric("Datasets", dataset_count)

    st.markdown(
        f"""
        <div class="neo-card neo-card-cyan">
          <div class="eyebrow">REPOSITORY DETECTED</div>
          <h2 style="margin-bottom:4px">{escape(repo['owner'])}/
          {escape(repo['name'])}</h2>
          <p>{escape(meta.get('description') or 'No repository description provided.')}</p>
          <span class="pill">★ {meta.get('stargazers_count', 0)} stars</span>
          <span class="pill">⑂ {meta.get('forks_count', 0)} forks</span>
          <span class="pill">Branch: {escape(repo['branch'])}</span>
          <span class="pill">Language: {escape(str(meta.get('language') or 'Not specified'))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if repo.get("tree_truncated"):
        st.warning(
            "GitHub marked the file tree as truncated. The app loaded the readable "
            "files it could retrieve, but very large repositories may have files omitted."
        )


def render_file_explorer(repo):
    st.markdown("## 🗂️ Choose your learning mission")
    st.write("Pick one file. Learn it first, then test what you understood.")

    file_paths = list(repo["files"].keys())
    if not file_paths:
        st.info("No readable files were found.")
        return None

    def label(path):
        return f"{file_kind(path)}  ·  {path}"

    selected = st.selectbox(
        "Select a repository file",
        options=file_paths,
        format_func=label,
        key="file_picker",
    )
    st.session_state.selected_file = selected

    content = repo["files"][selected]
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.markdown(
            f'<div class="neo-card"><span class="eyebrow">FILE TYPE</span>'
            f'<h3>{escape(file_kind(selected))}</h3></div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="neo-card"><span class="eyebrow">FILE SIZE</span>'
            f'<h3>{len(content):,} characters</h3></div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            '<div class="neo-card"><span class="eyebrow">LEARNING MODE</span>'
            '<h3>Explain + Test</h3></div>',
            unsafe_allow_html=True,
        )

    with st.expander("Preview original file", expanded=False):
        st.code(content[:12000], language="sql" if selected.endswith(".sql") else None)
        if len(content) > 12000:
            st.caption("Preview shortened for readability; the download contains the retrieved file content.")

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "⬇️ Save original file",
            data=content.encode("utf-8"),
            file_name=Path(selected).name,
            mime="text/plain",
            key=f"download_source_{selected}",
            use_container_width=True,
        )
    with d2:
        if st.button("⚡ Explain this file", key=f"explain_{selected}",
                     use_container_width=True):
            with st.spinner("Reading the file and preparing your explanation..."):
                try:
                    explanation = explain_file(repo, selected, content)
                    st.session_state.explanations[selected] = explanation
                    st.session_state.page = "Learn a File"
                except Exception as e:
                    st.error(f"Could not generate the explanation: {e}")

    explanation = st.session_state.explanations.get(selected)
    if explanation:
        st.markdown("---")
        st.markdown("## ✨ Your file breakdown")
        st.markdown(explanation)
        st.download_button(
            "⬇️ Download explanation (.txt)",
            data=explanation,
            file_name=f"{Path(selected).stem}_explanation.txt",
            mime="text/plain",
            key=f"download_explanation_{selected}",
        )
        pdf_bytes = create_pdf(
            f"Explanation — {selected}",
            f"# File: {selected}\n\n{explanation}",
        )
        st.download_button(
            "📄 Download explanation as PDF",
            data=pdf_bytes,
            file_name=f"{Path(selected).stem}_explanation.pdf",
            mime="application/pdf",
            key=f"download_pdf_{selected}",
        )

        st.markdown("---")
        st.markdown("### 🧠 Ready for your assessment?")
        st.write("The test contains 10 questions based on this file.")
        if st.button("🎯 Take test", key=f"take_test_{selected}",
                     use_container_width=True):
            if selected not in st.session_state.quizzes:
                with st.spinner("Building a file-specific 10-question quiz..."):
                    try:
                        st.session_state.quizzes[selected] = generate_quiz(
                            repo, selected, content
                        )
                        st.session_state.answers[selected] = {}
                        st.session_state.submitted[selected] = False
                    except Exception as e:
                        st.error(f"Could not create the assessment: {e}")
                        st.stop()
            st.session_state.page = "Take Test"
            st.rerun()

    return selected


def render_test():
    path = st.session_state.selected_file
    if not path or path not in st.session_state.quizzes:
        st.info("Choose a file and generate its assessment first.")
        return

    questions = st.session_state.quizzes[path]
    answers = st.session_state.answers.setdefault(path, {})
    submitted = st.session_state.submitted.get(path, False)

    st.markdown("## 🎯 MCQ Arcade")
    st.caption(f"Assessment file: `{path}`")
    st.progress(len(answers) / 10, text=f"{len(answers)} of 10 questions answered")

    for i, q in enumerate(questions):
        st.markdown(
            f'<div class="neo-card"><span class="eyebrow">QUESTION {i + 1:02d} / 10</span>'
            f'<h3>{escape(q["question"])}</h3></div>',
            unsafe_allow_html=True,
        )
        key = f"mcq_{path}_{i}"
        previous = answers.get(str(i))
        choice = st.radio(
            f"Choose an answer for question {i + 1}",
            options=list(range(4)),
            format_func=lambda n, opts=q["options"]: f"{chr(65+n)}. {opts[n]}",
            index=previous if previous is not None else None,
            key=key,
            disabled=submitted,
            label_visibility="collapsed",
        )
        if choice is not None:
            answers[str(i)] = choice

        if submitted:
            correct = q["answer"]
            if answers.get(str(i)) == correct:
                st.success(f"Correct! {q.get('explanation', '')}")
            else:
                st.error(
                    f"Incorrect. Correct answer: {chr(65+correct)}. "
                    f"{q['options'][correct]}\n\n{q.get('explanation', '')}"
                )

    if not submitted:
        if st.button("✅ Submit assessment", use_container_width=True):
            if len(answers) < 10:
                st.warning("Answer all 10 questions before submitting.")
            else:
                st.session_state.submitted[path] = True
                st.rerun()
    else:
        score = sum(
            answers.get(str(i)) == q["answer"]
            for i, q in enumerate(questions)
        )
        st.markdown(
            f'<div class="hero"><div class="eyebrow">ASSESSMENT COMPLETE</div>'
            f'<h1>{score}/10</h1><p>You completed the assessment for '
            f'<b>{escape(path)}</b>.</p></div>',
            unsafe_allow_html=True,
        )
        if score >= 8:
            st.success("Strong understanding. Try explaining the file without looking at the notes.")
        elif score >= 5:
            st.info("Good start. Review the explanation and revisit the questions you missed.")
        else:
            st.warning("Review the explanation once more, then retry the assessment.")

        if st.button("🔁 Retry this assessment", use_container_width=True):
            st.session_state.answers[path] = {}
            st.session_state.submitted[path] = False
            st.rerun()

        if st.button("🏠 Back to Home", use_container_width=True):
            st.session_state.page = "Home"
            st.rerun()


def render_interview(repo):
    st.markdown("## 🎤 Interview Q/A")
    st.write(
        "Ten concise questions based on the repository as a whole. "
        "Answers are kept short enough to practice aloud."
    )
    if st.session_state.interview_qa is None:
        if st.button("✨ Generate repository interview Q/A", use_container_width=True):
            with st.spinner("Reviewing repository context and preparing interview answers..."):
                try:
                    st.session_state.interview_qa = generate_interview_qa(repo)
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not generate interview Q/A: {e}")
        return

    qa = st.session_state.interview_qa
    lines = [f"# Interview Q/A — {repo['owner']}/{repo['name']}"]
    for i, item in enumerate(qa, 1):
        st.markdown(f"### {i}. {item['question']}")
        st.markdown(item["answer"])
        lines.append(f"## {i}. {item['question']}\n\n{item['answer']}\n")

    combined = "\n\n".join(lines)
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "⬇️ Save interview Q/A (.txt)",
            data=combined,
            file_name="repository_interview_qa.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "📄 Save interview Q/A (PDF)",
            data=create_pdf("Repository Interview Q/A", combined),
            file_name="repository_interview_qa.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    if st.button("🔄 Regenerate interview Q/A"):
        st.session_state.interview_qa = None
        st.rerun()


# ============================================================
# MAIN APPLICATION
# ============================================================

init_state()
render_hero()

with st.sidebar:
    st.markdown("## ⚡ CONTROL DECK")
    st.markdown(
        '<div class="neo-card neo-card-pink">'
        '<span class="eyebrow">YOUR WORKFLOW</span>'
        '<p>01 — Load a repo</p><p>02 — Learn a file</p>'
        '<p>03 — Take the quiz</p><p>04 — Prep for interviews</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = "Home"
        st.rerun()
    if st.button("🎯 Take Test", use_container_width=True):
        st.session_state.page = "Take Test"
        st.rerun()
    if st.button("🎤 Interview Q/A", use_container_width=True):
        st.session_state.page = "Interview Q/A"
        st.rerun()

    st.markdown("---")
    st.caption("Retro Neo-Pop • Built for curious developers")
    st.caption(f"AI model: `{MODEL}`")
    

if st.session_state.repo is None:
    st.markdown("### 🔗 Drop in a GitHub repository")
    st.write("Only the repository link is needed here. The app handles the rest.")
    with st.form("repo_form", clear_on_submit=False):
        repo_url = st.text_input(
            "GitHub repository URL",
            placeholder="https://github.com/owner/repository",
        )
        submit = st.form_submit_button(
            "🚀 Load my repository",
            use_container_width=True,
        )
    if submit:
        try:
            # Validate the URL before making any API requests.
            parse_github_url(repo_url)
            with st.spinner("Fetching repository files from GitHub..."):
                loaded = load_repository(repo_url)
            st.session_state.repo_url = repo_url
            st.session_state.repo = loaded
            st.session_state.files = loaded["files"]
            st.session_state.tree = loaded["tree"]
            st.session_state.readme = loaded["readme"]
            st.session_state.repo_error = None
            st.session_state.page = "Home"
            st.rerun()
        except Exception as e:
            st.session_state.repo_error = str(e)
            st.error(f"Could not load the repository: {e}")

    if st.session_state.repo_error:
        st.error(st.session_state.repo_error)

    st.markdown("---")
    st.markdown("### What you can do here")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="neo-card"><h3>📚 Learn</h3><p>Understand a selected file.</p></div>',
                    unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="neo-card"><h3>🧩 Practice</h3><p>Take a 10-question quiz.</p></div>',
                    unsafe_allow_html=True)
    st.stop()

repo = st.session_state.repo

# Top navigation buttons
nav1, nav2, nav3 = st.columns([1, 1, 1])
with nav1:
    if st.button("🏠 Repository Home", use_container_width=True):
        st.session_state.page = "Home"
        st.rerun()
with nav2:
    if st.button("🎯 File Assessment", use_container_width=True):
        st.session_state.page = "Take Test"
        st.rerun()
with nav3:
    if st.button("🎤 Interview Q/A", use_container_width=True):
        st.session_state.page = "Interview Q/A"
        st.rerun()

st.markdown("---")

if st.session_state.page == "Home":
    render_repo_overview(repo)
    render_file_explorer(repo)

    st.markdown("---")
    st.markdown("## 🏁 Your next move")
    st.markdown(
        '<div class="neo-card neo-card-lime">'
        '<h3>Learn every file. Then ace the interview.</h3>'
        '<p>Select a file above, generate its explanation, complete its 10-question '
        'assessment, and repeat for other files. When you are ready, open '
        '<b>Interview Q/A</b> for ten repository-wide questions with short answers.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

elif st.session_state.page == "Learn a File":
    render_repo_overview(repo)
    render_file_explorer(repo)

elif st.session_state.page == "Take Test":
    render_test()

elif st.session_state.page == "Interview Q/A":
    render_interview(repo)

st.markdown("---")
st.caption(
    "RepoRiot Project Lab • AI-generated explanations and quizzes should be "
    "checked against the actual repository before being used in production or interviews."
)
