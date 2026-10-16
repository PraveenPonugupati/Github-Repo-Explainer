#!/usr/bin/env python
# coding: utf-8

# In[53]:


get_ipython().run_line_magic('pip', 'install -q --upgrade streamlit requests groq reportlab')


# In[82]:


get_ipython().run_cell_magic('writefile', 'github_project_lab.py', 'import os\nimport re\nimport io\nimport json\nimport base64\nimport textwrap\nfrom pathlib import Path\nfrom xml.sax.saxutils import escape\n\nimport requests\nimport streamlit as st\nfrom groq import Groq\nfrom reportlab.lib import colors\nfrom reportlab.lib.enums import TA_LEFT\nfrom reportlab.lib.pagesizes import A4\nfrom reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle\nfrom reportlab.lib.units import mm\nfrom reportlab.platypus import (\n    SimpleDocTemplate, Paragraph, Spacer, Preformatted,\n    PageBreak, KeepTogether\n)\n\n# ============================================================\n# APP CONFIGURATION\n# ============================================================\n\nst.set_page_config(\n    page_title="RepoRiot | GitHub Project Lab",\n    page_icon="⚡",\n    layout="wide",\n    initial_sidebar_state="expanded",\n)\n\nGITHUB_API = "https://api.github.com"\nMODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")\nMAX_FILE_BYTES = 180_000\nMAX_REPO_FILES = 45\nMAX_CONTEXT_CHARS = 45_000\nREQUEST_TIMEOUT = 25\n\nTEXT_EXTENSIONS = {\n    ".py", ".ipynb", ".sql", ".md", ".txt", ".csv", ".tsv",\n    ".json", ".jsonl", ".yaml", ".yml", ".xml", ".html", ".css",\n    ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".h",\n    ".hpp", ".r", ".R", ".ipynb", ".sh", ".bat", ".ps1",\n    ".toml", ".ini", ".cfg", ".env.example", ".gitignore",\n    ".dockerfile", ".prisma", ".go", ".rs", ".php",\n}\n\nSKIP_DIRS = {\n    ".git", "node_modules", "venv", ".venv", "__pycache__",\n    "dist", "build", ".next", ".idea", ".vscode",\n}\n\n# ============================================================\n# RETRO NEO-POP THEME\n# ============================================================\n\nst.markdown("""\n<style>\n@import url(\'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap\');\n\n:root {\n    --ink: #f7f3ff;\n    --muted: #b9b1d0;\n    --bg: #100b20;\n    --panel: #1d1535;\n    --panel2: #271b43;\n    --pink: #ff4fa3;\n    --lime: #d8ff3e;\n    --cyan: #48e5ff;\n    --orange: #ffb454;\n}\n\nhtml, body, [class*="css"] {\n    font-family: \'Space Grotesk\', sans-serif;\n}\n.stApp {\n    background:\n        radial-gradient(ellipse at 5% 0%, #402052 0%, transparent 35%),\n        radial-gradient(ellipse at 100% 10%, #18364a 0%, transparent 28%),\n        var(--bg);\n    color: var(--ink);\n}\n[data-testid="stHeader"] {\n    background: rgba(16,11,32,.86);\n}\n[data-testid="stSidebar"] {\n    background: linear-gradient(180deg, #1b1231, #110c21);\n    border-right: 1px solid #46345f;\n}\nh1, h2, h3 {\n    color: var(--ink) !important;\n    letter-spacing: -0.035em;\n}\np, li, label, .stMarkdown {\n    color: var(--ink);\n}\n.hero {\n    border: 2px solid var(--pink);\n    border-radius: 24px;\n    padding: 30px 32px;\n    background: linear-gradient(120deg, #2b1748 0%, #1b183c 60%, #103242 100%);\n    box-shadow: 7px 7px 0 var(--pink);\n    margin: 8px 0 28px 0;\n}\n.eyebrow {\n    color: var(--lime);\n    font-family: \'Space Mono\', monospace;\n    text-transform: uppercase;\n    letter-spacing: .14em;\n    font-size: .78rem;\n    font-weight: 700;\n}\n.hero h1 {\n    font-size: clamp(2.2rem, 5vw, 4rem);\n    line-height: 1.02;\n    margin: 10px 0;\n}\n.hero p {\n    color: #ddd5f1;\n    max-width: 800px;\n    font-size: 1.08rem;\n}\n.neo-card {\n    background: var(--panel);\n    border: 1px solid #55416f;\n    border-radius: 18px;\n    padding: 20px;\n    margin: 10px 0;\n}\n.neo-card-pink {\n    border: 1.5px solid var(--pink);\n    box-shadow: 4px 4px 0 #702c62;\n}\n.neo-card-lime {\n    border: 1.5px solid var(--lime);\n    box-shadow: 4px 4px 0 #536021;\n}\n.neo-card-cyan {\n    border: 1.5px solid var(--cyan);\n    box-shadow: 4px 4px 0 #235a68;\n}\n.pill {\n    display: inline-block;\n    padding: 5px 10px;\n    margin: 3px 5px 3px 0;\n    border-radius: 999px;\n    background: #34264d;\n    border: 1px solid #665080;\n    color: #f7f3ff;\n    font-family: \'Space Mono\', monospace;\n    font-size: .76rem;\n}\n.mono {\n    font-family: \'Space Mono\', monospace;\n    color: var(--lime);\n}\ndiv.stButton > button, div.stDownloadButton > button {\n    border: 1.5px solid var(--lime);\n    border-radius: 12px;\n    background: var(--lime);\n    color: #171024;\n    font-weight: 800;\n    min-height: 2.8rem;\n    transition: transform .12s ease, box-shadow .12s ease;\n}\ndiv.stButton > button:hover, div.stDownloadButton > button:hover {\n    transform: translate(-2px, -2px);\n    box-shadow: 4px 4px 0 var(--pink);\n    border-color: var(--pink);\n    color: #171024;\n}\ndiv.stButton > button[kind="secondary"] {\n    background: #2a2043;\n    color: var(--ink);\n    border-color: #755a91;\n}\ndiv[data-testid="stTextInput"] input {\n    background: #1c1431;\n    color: white;\n    border: 1.5px solid #73558e;\n    border-radius: 12px;\n}\ndiv[data-testid="stSelectbox"] > div > div {\n    background: #1c1431;\n    border-radius: 10px;\n}\n[data-testid="stMetric"] {\n    background: #211738;\n    border: 1px solid #49365f;\n    border-radius: 14px;\n    padding: 14px;\n}\n[data-testid="stMetricLabel"] {\n    color: #c8bbdf !important;\n}\n[data-testid="stMetricValue"] {\n    color: var(--lime) !important;\n}\nhr {\n    border-color: #49365f;\n}\ndiv[data-testid="stExpander"] {\n    border: 1px solid #49365f;\n    border-radius: 12px;\n    background: #1a1230;\n}\n.stAlert {\n    border-radius: 12px;\n}\nfooter {visibility: hidden;}\n#MainMenu {visibility: hidden;}\n</style>\n""", unsafe_allow_html=True)\n\n\n# ============================================================\n# HELPERS: SESSION STATE AND API CLIENT\n# ============================================================\n\ndef init_state():\n    defaults = {\n        "repo_url": "",\n        "repo": None,\n        "files": {},\n        "tree": [],\n        "readme": "",\n        "selected_file": None,\n        "explanations": {},\n        "quizzes": {},\n        "answers": {},\n        "submitted": {},\n        "interview_qa": None,\n        "page": "Home",\n        "repo_error": None,\n    }\n    for key, value in defaults.items():\n        if key not in st.session_state:\n            st.session_state[key] = value\n\n\ndef get_client():\n    key = os.getenv("GROQ_API_KEY", "").strip()\n    if not key:\n        st.error(\n            "Groq API key was not passed to this Streamlit process. "\n            "Stop the app and relaunch it using the Jupyter launch cell below."\n        )\n        st.code(\n            "from getpass import getpass\\n"\n            "import os, subprocess, sys\\n"\n            "key = getpass(\'Enter Groq API key: \')\\n"\n            "env = os.environ.copy()\\n"\n            "env[\'GROQ_API_KEY\'] = key\\n"\n            "subprocess.Popen([sys.executable, \'-m\', \'streamlit\', \'run\', "\n            "\'github_project_lab.py\', \'--server.port\', \'8501\'], env=env)"\n        )\n        st.stop()\n    return Groq(api_key=key)\n\n\ndef ask_ai(prompt, system="You are a precise, practical software engineering tutor.",\n           max_tokens=4500, temperature=0.2):\n    client = get_client()\n    response = client.chat.completions.create(\n        model=MODEL,\n        messages=[\n            {"role": "system", "content": system},\n            {"role": "user", "content": prompt},\n        ],\n        temperature=temperature,\n        max_tokens=max_tokens,\n    )\n    return response.choices[0].message.content.strip()\n\n\ndef extract_json(text):\n    """Parse JSON even if the model surrounds it with Markdown fences."""\n    cleaned = re.sub(r"^```(?:json)?\\s*", "", text.strip(), flags=re.I)\n    cleaned = re.sub(r"\\s*```$", "", cleaned)\n    try:\n        return json.loads(cleaned)\n    except json.JSONDecodeError:\n        start = cleaned.find("{")\n        end = cleaned.rfind("}")\n        if start >= 0 and end > start:\n            return json.loads(cleaned[start:end + 1])\n        raise ValueError("The AI response did not contain valid JSON.")\n\n\n# ============================================================\n# GITHUB REPOSITORY FUNCTIONS\n# ============================================================\n\ndef parse_github_url(url):\n    url = url.strip().rstrip("/")\n    url = re.sub(r"\\.git$", "", url)\n    match = re.match(\n        r"^(?:https?://)?(?:www\\.)?github\\.com/([^/\\s]+)/([^/\\s]+)(?:/.*)?$",\n        url,\n        re.I,\n    )\n    if not match:\n        raise ValueError(\n            "Enter a GitHub repository URL like "\n            "https://github.com/owner/repository"\n        )\n    owner, repo = match.group(1), match.group(2)\n    if owner in {"settings", "features", "topics", "orgs", "marketplace"}:\n        raise ValueError("That looks like a GitHub page, not a repository URL.")\n    return owner, repo\n\n\ndef github_get(path, params=None):\n    headers = {\n        "Accept": "application/vnd.github+json",\n        "X-GitHub-Api-Version": "2022-11-28",\n        "User-Agent": "RepoRiot-GitHub-Project-Lab",\n    }\n    # Optional token can improve GitHub API rate limits.\n    # Public repositories work without one.\n    token = os.getenv("GITHUB_TOKEN", "").strip()\n    if token:\n        headers["Authorization"] = f"Bearer {token}"\n\n    response = requests.get(\n        f"{GITHUB_API}{path}",\n        headers=headers,\n        params=params,\n        timeout=REQUEST_TIMEOUT,\n    )\n    if response.status_code == 404:\n        raise ValueError(\n            "Repository or file not found. Check the URL and confirm "\n            "that the repository is public."\n        )\n    if response.status_code == 403:\n        raise ValueError(\n            "GitHub API rate limit reached. Wait a little and try again, "\n            "or optionally configure a GitHub token in the notebook environment."\n        )\n    response.raise_for_status()\n    return response.json()\n\n\ndef is_text_file(path):\n    p = Path(path)\n    name = p.name.lower()\n    if any(part.lower() in SKIP_DIRS for part in p.parts):\n        return False\n    if name in {"dockerfile", "makefile", "license", "readme"}:\n        return True\n    return p.suffix.lower() in TEXT_EXTENSIONS\n\n\ndef load_repository(url):\n    owner, repo_name = parse_github_url(url)\n    base = f"/repos/{owner}/{repo_name}"\n    metadata = github_get(base)\n\n    branch = metadata.get("default_branch") or "main"\n    tree_data = github_get(\n        f"{base}/git/trees/{branch}",\n        params={"recursive": "1"},\n    )\n    tree = tree_data.get("tree", [])\n\n    # If the recursive tree is truncated, keep the available entries.\n    tree = [\n        item for item in tree\n        if item.get("type") == "blob"\n        and item.get("path")\n        and is_text_file(item["path"])\n        and item.get("size", 0) <= MAX_FILE_BYTES\n    ][:MAX_REPO_FILES]\n\n    files = {}\n    readme = ""\n\n    for item in tree:\n        path = item["path"]\n        try:\n            content_data = github_get(f"{base}/contents/{path}")\n            encoded = content_data.get("content", "")\n            if content_data.get("encoding") == "base64":\n                raw = base64.b64decode(encoded)\n                content = raw.decode("utf-8", errors="replace")\n            else:\n                content = content_data.get("content", "")\n            files[path] = content[:MAX_FILE_BYTES]\n            if Path(path).name.lower().startswith("readme") and not readme:\n                readme = content[:MAX_FILE_BYTES]\n        except (requests.RequestException, ValueError, KeyError):\n            # Skip individual files that cannot be fetched; keep other files.\n            continue\n\n    # If README was not in the tree, check the standard endpoint.\n    if not readme:\n        try:\n            data = github_get(f"{base}/readme")\n            if data.get("encoding") == "base64":\n                readme = base64.b64decode(data["content"]).decode(\n                    "utf-8", errors="replace"\n                )\n            if readme:\n                files.setdefault(data.get("path", "README.md"), readme)\n        except Exception:\n            pass\n\n    if not files:\n        raise ValueError(\n            "I couldn\'t retrieve readable files. The repository may be empty, "\n            "private, or mostly contain unsupported/binary file types."\n        )\n\n    return {\n        "metadata": metadata,\n        "owner": owner,\n        "name": repo_name,\n        "branch": branch,\n        "files": files,\n        "readme": readme,\n        "tree": tree,\n        "tree_truncated": tree_data.get("truncated", False),\n    }\n\n\ndef file_kind(path):\n    suffix = Path(path).suffix.lower()\n    name = Path(path).name.lower()\n    if suffix == ".csv" or suffix == ".tsv":\n        return "Dataset"\n    if suffix == ".sql":\n        return "SQL"\n    if suffix == ".ipynb":\n        return "Notebook"\n    if suffix == ".py":\n        return "Python"\n    if name.startswith("readme"):\n        return "README"\n    if suffix in {".json", ".yaml", ".yml", ".toml"}:\n        return "Configuration / data"\n    return suffix.lstrip(".").upper() or "Text"\n\n\ndef make_repo_context(repo):\n    chunks = []\n    total = 0\n    meta = repo["metadata"]\n    chunks.append(\n        f"REPOSITORY: {repo[\'owner\']}/{repo[\'name\']}\\n"\n        f"DESCRIPTION: {meta.get(\'description\') or \'Not provided\'}\\n"\n        f"LANGUAGES: {json.dumps(meta.get(\'language\'))}\\n"\n        f"DEFAULT BRANCH: {repo[\'branch\']}\\n"\n    )\n    for path, content in repo["files"].items():\n        piece = f"\\n\\n===== FILE: {path} =====\\n{content[:5000]}"\n        if total + len(piece) > MAX_CONTEXT_CHARS:\n            break\n        chunks.append(piece)\n        total += len(piece)\n    return "\\n".join(chunks)\n\n\n# ============================================================\n# EXPLANATIONS, MCQ ASSESSMENTS, AND INTERVIEW QUESTIONS\n# ============================================================\n\ndef explain_file(repo, path, content):\n    kind = file_kind(path)\n    prompt = f"""\nExplain this repository file for a learner preparing for a technical interview.\n\nRepository: {repo[\'owner\']}/{repo[\'name\']}\nRepository description: {repo[\'metadata\'].get(\'description\') or \'Not supplied\'}\nFile path: {path}\nFile type: {kind}\n\nRequirements:\n- Start with the purpose of this exact file.\n- Explain the important sections and the order in which they work.\n- Explain important variables, functions, classes, transformations, and dependencies.\n- For SQL, explain each query, joins, filters, aggregations, CTEs, window functions,\n  and the business question each query answers, if present.\n- For CSV/TSV data, explain column names, likely data types, sample values,\n  target/label columns only when supported by the data, and data-quality concerns.\n  Do not claim that unseen rows or undocumented labels exist.\n- For notebooks, explain markdown, code cells, data flow, and model steps.\n- For README files, explain setup, usage, architecture, and claimed results.\n- If code is long, explain it in logical blocks and include line numbers where feasible.\n- Separate facts directly visible in the file from reasonable inferences.\n- Mention limitations, potential bugs, and interview talking points.\n- Use clear headings and practical examples. Do not invent project details.\n\nFILE CONTENT:\n```text\n{content[:MAX_FILE_BYTES]}\n```\n"""\n    return ask_ai(\n        prompt,\n        system="You are a meticulous senior engineer and patient technical interviewer.",\n        max_tokens=5000,\n    )\n\n\ndef generate_quiz(repo, path, content):\n    prompt = f"""\nCreate exactly 10 multiple-choice assessment questions about the specific file below.\nQuestions must test actual understanding, not generic trivia.\n\nRepository: {repo[\'owner\']}/{repo[\'name\']}\nFile: {path}\nFile type: {file_kind(path)}\n\nFor a dataset, test real columns, values, data types, labels only if evident,\nand data-quality interpretation. For SQL, test the actual query logic, joins,\nfilters, grouping, aggregation, CTEs or window functions that appear.\nFor source code, test actual functions, variables, logic, libraries, and data flow.\nFor README/config files, test documented setup, architecture, and behavior.\n\nRules:\n- Exactly 10 questions.\n- Four options per question.\n- Exactly one correct option.\n- Explanations must be short and tied to the file.\n- Never make up columns, functions, query behavior, or outputs.\n- If information is not present in the file, don\'t ask about it.\n\nReturn ONLY valid JSON in this shape:\n{{\n  "questions": [\n    {{\n      "question": "Question text",\n      "options": ["A", "B", "C", "D"],\n      "answer": 0,\n      "explanation": "Short reason"\n    }}\n  ]\n}}\n\nFILE CONTENT:\n```text\n{content[:MAX_FILE_BYTES]}\n```\n"""\n    data = extract_json(ask_ai(\n        prompt,\n        system="You create accurate file-specific assessments. Output valid JSON only.",\n        max_tokens=3500,\n        temperature=0.1,\n    ))\n    questions = data.get("questions", [])\n    if len(questions) != 10:\n        raise ValueError("The AI did not return exactly 10 questions. Please retry.")\n    for q in questions:\n        if len(q.get("options", [])) != 4 or q.get("answer") not in [0, 1, 2, 3]:\n            raise ValueError("The generated quiz had an invalid question format.")\n    return questions\n\n\ndef generate_interview_qa(repo):\n    context = limit_repo_context(make_repo_context(repo), max_chars=12000)\n    prompt = f"""\nCreate 10 high-value technical interview questions and answers about the WHOLE\nrepository, using the repository context below.\n\nInclude a balanced selection covering:\n- Project purpose and end-to-end workflow.\n- Dataset source, columns, target/labels, and preprocessing only if supported.\n- Important code files, functions, dependencies, and architecture.\n- SQL business questions and actual query logic if SQL exists.\n- Model/algorithm and evaluation metrics only if the repository supports them.\n- Design decisions, limitations, validation, and possible improvements.\n\nAnswers must be concise: no more than 5 lines each. Use exact names and evidence\nfrom the files wherever possible. If the repository doesn\'t provide an answer,\nsay "The repository does not specify this" rather than inventing details.\nDo not create generic questions that ignore the project\'s actual content.\nReturn ONLY valid JSON:\n{{\n  "qa": [\n    {{"question": "Question?", "answer": "Answer in at most 5 lines."}}\n  ]\n}}\n\nRepository context:\n{context}\n"""\n    data = extract_json(ask_ai(\n        prompt,\n        system="You are a senior technical interviewer. Be accurate, specific, and concise.",\n        max_tokens=4000,\n        temperature=0.15,\n    ))\n    qa = data.get("qa", [])\n    if len(qa) != 10:\n        raise ValueError("The AI did not return exactly 10 interview Q/A pairs.")\n    return qa\n\n\n# ============================================================\n# PDF EXPORT\n# ============================================================\n\ndef create_pdf(title, body):\n    buffer = io.BytesIO()\n    doc = SimpleDocTemplate(\n        buffer,\n        pagesize=A4,\n        rightMargin=18 * mm,\n        leftMargin=18 * mm,\n        topMargin=18 * mm,\n        bottomMargin=18 * mm,\n        title=title,\n        author="RepoRiot GitHub Project Lab",\n    )\n\n    styles = getSampleStyleSheet()\n    styles.add(ParagraphStyle(\n        name="NeoTitle", parent=styles["Title"], fontName="Helvetica-Bold",\n        fontSize=22, leading=27, textColor=colors.HexColor("#5A267D"),\n        alignment=TA_LEFT, spaceAfter=12,\n    ))\n    styles.add(ParagraphStyle(\n        name="NeoHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",\n        fontSize=14, leading=18, textColor=colors.HexColor("#A51D72"),\n        spaceBefore=12, spaceAfter=6,\n    ))\n    styles.add(ParagraphStyle(\n        name="NeoBody", parent=styles["BodyText"], fontName="Helvetica",\n        fontSize=9.5, leading=14, spaceAfter=7,\n        textColor=colors.HexColor("#252033"),\n    ))\n    styles.add(ParagraphStyle(\n        name="NeoCode", parent=styles["Code"], fontName="Courier",\n        fontSize=7.5, leading=10, backColor=colors.HexColor("#F0ECF8"),\n        borderPadding=6, spaceAfter=8,\n    ))\n\n    story = [Paragraph(escape(title), styles["NeoTitle"])]\n    story.append(Paragraph(\n        "Generated by RepoRiot — GitHub Project Lab",\n        styles["NeoBody"],\n    ))\n    story.append(Spacer(1, 8))\n\n    # Convert Markdown-like text into safe PDF paragraphs.\n    in_code = False\n    code_lines = []\n\n    def flush_code():\n        nonlocal code_lines\n        if code_lines:\n            story.append(Preformatted("\\n".join(code_lines), styles["NeoCode"]))\n            code_lines = []\n\n    for line in body.splitlines():\n        stripped = line.strip()\n\n        if stripped.startswith("```"):\n            if not in_code:\n                in_code = True\n            else:\n                in_code = False\n                flush_code()\n            continue\n\n        if in_code:\n            code_lines.append(line[:180])\n            continue\n\n        if not stripped:\n            story.append(Spacer(1, 4))\n        elif stripped.startswith("# "):\n            story.append(Paragraph(escape(stripped[2:]), styles["NeoTitle"]))\n        elif stripped.startswith("## ") or stripped.startswith("### "):\n            story.append(Paragraph(escape(stripped.lstrip("# ")), styles["NeoHeading"]))\n        elif stripped.startswith(("- ", "* ")):\n            story.append(Paragraph(\n                "&#8226; " + escape(stripped[2:]), styles["NeoBody"]\n            ))\n        elif re.match(r"^\\d+[\\.)]\\s", stripped):\n            story.append(Paragraph(escape(stripped), styles["NeoBody"]))\n        else:\n            safe = escape(stripped)\n            safe = re.sub(r"\\*\\*(.+?)\\*\\*", r"<b>\\1</b>", safe)\n            safe = re.sub(r"`(.+?)`", r"<font name=\'Courier\'>\\1</font>", safe)\n            story.append(Paragraph(safe, styles["NeoBody"]))\n\n    flush_code()\n    doc.build(story)\n    buffer.seek(0)\n    return buffer.getvalue()\n\n\n# ============================================================\n# REUSABLE UI\n# ============================================================\n\ndef render_hero():\n    st.markdown("""\n    <div class="hero">\n      <div class="eyebrow">✦ Learn the code. Own the interview. ✦</div>\n      <h1>RepoRiot <span style="color:#d8ff3e">Project Lab</span></h1>\n      <p>Your GitHub repository, turned into a hands-on learning studio.\n      Explore files, understand the logic, test yourself, and get interview-ready.</p>\n      <span class="pill">AI CODE EXPLAINER</span>\n      <span class="pill">FILE-BY-FILE LEARNING</span>\n      <span class="pill">MCQ ARCADE</span>\n      <span class="pill">PDF EXPORTS</span>\n    </div>\n    """, unsafe_allow_html=True)\n\n\ndef render_repo_overview(repo):\n    meta = repo["metadata"]\n    files = repo["files"]\n    python_count = sum(Path(p).suffix.lower() == ".py" for p in files)\n    sql_count = sum(Path(p).suffix.lower() == ".sql" for p in files)\n    dataset_count = sum(Path(p).suffix.lower() in {".csv", ".tsv"} for p in files)\n\n    cols = st.columns(4)\n    cols[0].metric("Readable files", len(files))\n    cols[1].metric("Python files", python_count)\n    cols[2].metric("SQL files", sql_count)\n    cols[3].metric("Datasets", dataset_count)\n\n    st.markdown(\n        f"""\n        <div class="neo-card neo-card-cyan">\n          <div class="eyebrow">REPOSITORY DETECTED</div>\n          <h2 style="margin-bottom:4px">{escape(repo[\'owner\'])}/\n          {escape(repo[\'name\'])}</h2>\n          <p>{escape(meta.get(\'description\') or \'No repository description provided.\')}</p>\n          <span class="pill">★ {meta.get(\'stargazers_count\', 0)} stars</span>\n          <span class="pill">⑂ {meta.get(\'forks_count\', 0)} forks</span>\n          <span class="pill">Branch: {escape(repo[\'branch\'])}</span>\n          <span class="pill">Language: {escape(str(meta.get(\'language\') or \'Not specified\'))}</span>\n        </div>\n        """,\n        unsafe_allow_html=True,\n    )\n\n    if repo.get("tree_truncated"):\n        st.warning(\n            "GitHub marked the file tree as truncated. The app loaded the readable "\n            "files it could retrieve, but very large repositories may have files omitted."\n        )\n\n\ndef render_file_explorer(repo):\n    st.markdown("## 🗂️ Choose your learning mission")\n    st.write("Pick one file. Learn it first, then test what you understood.")\n\n    file_paths = list(repo["files"].keys())\n    if not file_paths:\n        st.info("No readable files were found.")\n        return None\n\n    def label(path):\n        return f"{file_kind(path)}  ·  {path}"\n\n    selected = st.selectbox(\n        "Select a repository file",\n        options=file_paths,\n        format_func=label,\n        key="file_picker",\n    )\n    st.session_state.selected_file = selected\n\n    content = repo["files"][selected]\n    col1, col2, col3 = st.columns([1, 1, 1])\n    with col1:\n        st.markdown(\n            f\'<div class="neo-card"><span class="eyebrow">FILE TYPE</span>\'\n            f\'<h3>{escape(file_kind(selected))}</h3></div>\',\n            unsafe_allow_html=True,\n        )\n    with col2:\n        st.markdown(\n            f\'<div class="neo-card"><span class="eyebrow">FILE SIZE</span>\'\n            f\'<h3>{len(content):,} characters</h3></div>\',\n            unsafe_allow_html=True,\n        )\n    with col3:\n        st.markdown(\n            \'<div class="neo-card"><span class="eyebrow">LEARNING MODE</span>\'\n            \'<h3>Explain + Test</h3></div>\',\n            unsafe_allow_html=True,\n        )\n\n    with st.expander("Preview original file", expanded=False):\n        st.code(content[:12000], language="sql" if selected.endswith(".sql") else None)\n        if len(content) > 12000:\n            st.caption("Preview shortened for readability; the download contains the retrieved file content.")\n\n    d1, d2 = st.columns(2)\n    with d1:\n        st.download_button(\n            "⬇️ Save original file",\n            data=content.encode("utf-8"),\n            file_name=Path(selected).name,\n            mime="text/plain",\n            key=f"download_source_{selected}",\n            use_container_width=True,\n        )\n    with d2:\n        if st.button("⚡ Explain this file", key=f"explain_{selected}",\n                     use_container_width=True):\n            with st.spinner("Reading the file and preparing your explanation..."):\n                try:\n                    explanation = explain_file(repo, selected, content)\n                    st.session_state.explanations[selected] = explanation\n                    st.session_state.page = "Learn a File"\n                except Exception as e:\n                    st.error(f"Could not generate the explanation: {e}")\n\n    explanation = st.session_state.explanations.get(selected)\n    if explanation:\n        st.markdown("---")\n        st.markdown("## ✨ Your file breakdown")\n        st.markdown(explanation)\n        st.download_button(\n            "⬇️ Download explanation (.txt)",\n            data=explanation,\n            file_name=f"{Path(selected).stem}_explanation.txt",\n            mime="text/plain",\n            key=f"download_explanation_{selected}",\n        )\n        pdf_bytes = create_pdf(\n            f"Explanation — {selected}",\n            f"# File: {selected}\\n\\n{explanation}",\n        )\n        st.download_button(\n            "📄 Download explanation as PDF",\n            data=pdf_bytes,\n            file_name=f"{Path(selected).stem}_explanation.pdf",\n            mime="application/pdf",\n            key=f"download_pdf_{selected}",\n        )\n\n        st.markdown("---")\n        st.markdown("### 🧠 Ready for your assessment?")\n        st.write("The test contains 10 questions based on this file.")\n        if st.button("🎯 Take test", key=f"take_test_{selected}",\n                     use_container_width=True):\n            if selected not in st.session_state.quizzes:\n                with st.spinner("Building a file-specific 10-question quiz..."):\n                    try:\n                        st.session_state.quizzes[selected] = generate_quiz(\n                            repo, selected, content\n                        )\n                        st.session_state.answers[selected] = {}\n                        st.session_state.submitted[selected] = False\n                    except Exception as e:\n                        st.error(f"Could not create the assessment: {e}")\n                        st.stop()\n            st.session_state.page = "Take Test"\n            st.rerun()\n\n    return selected\n\n\ndef render_test():\n    path = st.session_state.selected_file\n    if not path or path not in st.session_state.quizzes:\n        st.info("Choose a file and generate its assessment first.")\n        return\n\n    questions = st.session_state.quizzes[path]\n    answers = st.session_state.answers.setdefault(path, {})\n    submitted = st.session_state.submitted.get(path, False)\n\n    st.markdown("## 🎯 MCQ Arcade")\n    st.caption(f"Assessment file: `{path}`")\n    st.progress(len(answers) / 10, text=f"{len(answers)} of 10 questions answered")\n\n    for i, q in enumerate(questions):\n        st.markdown(\n            f\'<div class="neo-card"><span class="eyebrow">QUESTION {i + 1:02d} / 10</span>\'\n            f\'<h3>{escape(q["question"])}</h3></div>\',\n            unsafe_allow_html=True,\n        )\n        key = f"mcq_{path}_{i}"\n        previous = answers.get(str(i))\n        choice = st.radio(\n            f"Choose an answer for question {i + 1}",\n            options=list(range(4)),\n            format_func=lambda n, opts=q["options"]: f"{chr(65+n)}. {opts[n]}",\n            index=previous if previous is not None else None,\n            key=key,\n            disabled=submitted,\n            label_visibility="collapsed",\n        )\n        if choice is not None:\n            answers[str(i)] = choice\n\n        if submitted:\n            correct = q["answer"]\n            if answers.get(str(i)) == correct:\n                st.success(f"Correct! {q.get(\'explanation\', \'\')}")\n            else:\n                st.error(\n                    f"Incorrect. Correct answer: {chr(65+correct)}. "\n                    f"{q[\'options\'][correct]}\\n\\n{q.get(\'explanation\', \'\')}"\n                )\n\n    if not submitted:\n        if st.button("✅ Submit assessment", use_container_width=True):\n            if len(answers) < 10:\n                st.warning("Answer all 10 questions before submitting.")\n            else:\n                st.session_state.submitted[path] = True\n                st.rerun()\n    else:\n        score = sum(\n            answers.get(str(i)) == q["answer"]\n            for i, q in enumerate(questions)\n        )\n        st.markdown(\n            f\'<div class="hero"><div class="eyebrow">ASSESSMENT COMPLETE</div>\'\n            f\'<h1>{score}/10</h1><p>You completed the assessment for \'\n            f\'<b>{escape(path)}</b>.</p></div>\',\n            unsafe_allow_html=True,\n        )\n        if score >= 8:\n            st.success("Strong understanding. Try explaining the file without looking at the notes.")\n        elif score >= 5:\n            st.info("Good start. Review the explanation and revisit the questions you missed.")\n        else:\n            st.warning("Review the explanation once more, then retry the assessment.")\n\n        if st.button("🔁 Retry this assessment", use_container_width=True):\n            st.session_state.answers[path] = {}\n            st.session_state.submitted[path] = False\n            st.rerun()\n\n        if st.button("🏠 Back to Home", use_container_width=True):\n            st.session_state.page = "Home"\n            st.rerun()\n\n\ndef render_interview(repo):\n    st.markdown("## 🎤 Interview Q/A")\n    st.write(\n        "Ten concise questions based on the repository as a whole. "\n        "Answers are kept short enough to practice aloud."\n    )\n    if st.session_state.interview_qa is None:\n        if st.button("✨ Generate repository interview Q/A", use_container_width=True):\n            with st.spinner("Reviewing repository context and preparing interview answers..."):\n                try:\n                    st.session_state.interview_qa = generate_interview_qa(repo)\n                    st.rerun()\n                except Exception as e:\n                    st.error(f"Could not generate interview Q/A: {e}")\n        return\n\n    qa = st.session_state.interview_qa\n    lines = [f"# Interview Q/A — {repo[\'owner\']}/{repo[\'name\']}"]\n    for i, item in enumerate(qa, 1):\n        st.markdown(f"### {i}. {item[\'question\']}")\n        st.markdown(item["answer"])\n        lines.append(f"## {i}. {item[\'question\']}\\n\\n{item[\'answer\']}\\n")\n\n    combined = "\\n\\n".join(lines)\n    c1, c2 = st.columns(2)\n    with c1:\n        st.download_button(\n            "⬇️ Save interview Q/A (.txt)",\n            data=combined,\n            file_name="repository_interview_qa.txt",\n            mime="text/plain",\n            use_container_width=True,\n        )\n    with c2:\n        st.download_button(\n            "📄 Save interview Q/A (PDF)",\n            data=create_pdf("Repository Interview Q/A", combined),\n            file_name="repository_interview_qa.pdf",\n            mime="application/pdf",\n            use_container_width=True,\n        )\n    if st.button("🔄 Regenerate interview Q/A"):\n        st.session_state.interview_qa = None\n        st.rerun()\n\n\n# ============================================================\n# MAIN APPLICATION\n# ============================================================\n\ninit_state()\nrender_hero()\n\nwith st.sidebar:\n    st.markdown("## ⚡ CONTROL DECK")\n    st.markdown(\n        \'<div class="neo-card neo-card-pink">\'\n        \'<span class="eyebrow">YOUR WORKFLOW</span>\'\n        \'<p>01 — Load a repo</p><p>02 — Learn a file</p>\'\n        \'<p>03 — Take the quiz</p><p>04 — Prep for interviews</p>\'\n        \'</div>\',\n        unsafe_allow_html=True,\n    )\n    if st.button("🏠 Home", use_container_width=True):\n        st.session_state.page = "Home"\n        st.rerun()\n    if st.button("🎯 Take Test", use_container_width=True):\n        st.session_state.page = "Take Test"\n        st.rerun()\n    if st.button("🎤 Interview Q/A", use_container_width=True):\n        st.session_state.page = "Interview Q/A"\n        st.rerun()\n\n    st.markdown("---")\n    st.caption("Retro Neo-Pop • Built for curious developers")\n    st.caption(f"AI model: `{MODEL}`")\n    \n\nif st.session_state.repo is None:\n    st.markdown("### 🔗 Drop in a GitHub repository")\n    st.write("Only the repository link is needed here. The app handles the rest.")\n    with st.form("repo_form", clear_on_submit=False):\n        repo_url = st.text_input(\n            "GitHub repository URL",\n            placeholder="https://github.com/owner/repository",\n        )\n        submit = st.form_submit_button(\n            "🚀 Load my repository",\n            use_container_width=True,\n        )\n    if submit:\n        try:\n            # Validate the URL before making any API requests.\n            parse_github_url(repo_url)\n            with st.spinner("Fetching repository files from GitHub..."):\n                loaded = load_repository(repo_url)\n            st.session_state.repo_url = repo_url\n            st.session_state.repo = loaded\n            st.session_state.files = loaded["files"]\n            st.session_state.tree = loaded["tree"]\n            st.session_state.readme = loaded["readme"]\n            st.session_state.repo_error = None\n            st.session_state.page = "Home"\n            st.rerun()\n        except Exception as e:\n            st.session_state.repo_error = str(e)\n            st.error(f"Could not load the repository: {e}")\n\n    if st.session_state.repo_error:\n        st.error(st.session_state.repo_error)\n\n    st.markdown("---")\n    st.markdown("### What you can do here")\n    c1, c2 = st.columns(2)\n    with c1:\n        st.markdown(\'<div class="neo-card"><h3>📚 Learn</h3><p>Understand a selected file.</p></div>\',\n                    unsafe_allow_html=True)\n    with c2:\n        st.markdown(\'<div class="neo-card"><h3>🧩 Practice</h3><p>Take a 10-question quiz.</p></div>\',\n                    unsafe_allow_html=True)\n    st.stop()\n\nrepo = st.session_state.repo\n\n# Top navigation buttons\nnav1, nav2, nav3 = st.columns([1, 1, 1])\nwith nav1:\n    if st.button("🏠 Repository Home", use_container_width=True):\n        st.session_state.page = "Home"\n        st.rerun()\nwith nav2:\n    if st.button("🎯 File Assessment", use_container_width=True):\n        st.session_state.page = "Take Test"\n        st.rerun()\nwith nav3:\n    if st.button("🎤 Interview Q/A", use_container_width=True):\n        st.session_state.page = "Interview Q/A"\n        st.rerun()\n\nst.markdown("---")\n\nif st.session_state.page == "Home":\n    render_repo_overview(repo)\n    render_file_explorer(repo)\n\n    st.markdown("---")\n    st.markdown("## 🏁 Your next move")\n    st.markdown(\n        \'<div class="neo-card neo-card-lime">\'\n        \'<h3>Learn every file. Then ace the interview.</h3>\'\n        \'<p>Select a file above, generate its explanation, complete its 10-question \'\n        \'assessment, and repeat for other files. When you are ready, open \'\n        \'<b>Interview Q/A</b> for ten repository-wide questions with short answers.</p>\'\n        \'</div>\',\n        unsafe_allow_html=True,\n    )\n\nelif st.session_state.page == "Learn a File":\n    render_repo_overview(repo)\n    render_file_explorer(repo)\n\nelif st.session_state.page == "Take Test":\n    render_test()\n\nelif st.session_state.page == "Interview Q/A":\n    render_interview(repo)\n\nst.markdown("---")\nst.caption(\n    "RepoRiot Project Lab • AI-generated explanations and quizzes should be "\n    "checked against the actual repository before being used in production or interviews."\n)\n')


# In[83]:


from pathlib import Path
import ast

FILE_PATH = Path("github_project_lab.py")

source = FILE_PATH.read_text(encoding="utf-8")

helper = '''

def make_limited_repo_context(repo, max_chars=10000):
    """Keep repository context small enough for Groq requests."""
    context = make_repo_context(repo)

    if not isinstance(context, str):
        context = str(context)

    if len(context) > max_chars:
        context = (
            context[:max_chars]
            + "\\n\\n[Repository context truncated to fit the AI request.]"
        )

    return context

'''

if "def make_limited_repo_context(" not in source:
    # Add the helper immediately before the PDF export section.
    marker = "# PDF EXPORT"
    if marker not in source:
        raise ValueError(
            "Could not find the PDF EXPORT section. "
            "Add the helper manually near make_repo_context()."
        )

    source = source.replace(marker, helper + "\n" + marker, 1)

ast.parse(source)
FILE_PATH.write_text(source, encoding="utf-8")

print("Helper added successfully.")


# In[84]:


# ============================================================
# 3. REPLACE FUNCTIONS USING AST, NOT SECTION-MARKER REGEX
# ============================================================

# Parse the original source and locate the actual function
# definitions. This does not depend on parameter names or
# comments such as "PDF EXPORT" and "MAIN APPLICATION".

try:
    tree = ast.parse(source)
except SyntaxError as e:
    raise SyntaxError(
        f"Original file has invalid Python syntax at "
        f"line {e.lineno}: {e.msg}. File not modified."
    ) from e


# Find module-level function definitions.
functions = {
    node.name: node
    for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
}

required_functions = {
    "generate_interview_qa": new_generate_function,
    "render_interview": new_render_function,
}

missing = [
    name for name in required_functions
    if name not in functions
]

if missing:
    raise ValueError(
        f"Could not find these functions in {app_path}: "
        f"{', '.join(missing)}. File not modified."
    )


# Prepare replacements using the original function line ranges.
# AST end_lineno identifies the last line of each function body.
replacements = []

for function_name, replacement_text in required_functions.items():
    node = functions[function_name]

    replacement_lines = (
        replacement_text.strip() + "\n"
    ).splitlines(keepends=True)

    replacements.append(
        (
            node.lineno - 1,
            node.end_lineno,
            replacement_lines,
            function_name,
        )
    )


# Replace from bottom to top so earlier line numbers remain valid.
lines = source.splitlines(keepends=True)

for start, end, replacement_lines, function_name in sorted(
    replacements,
    key=lambda item: item[0],
    reverse=True,
):
    lines[start:end] = replacement_lines

updated_source = "".join(lines)


# ============================================================
# 4. VALIDATE THE COMPLETE UPDATED FILE
# ============================================================

try:
    updated_tree = ast.parse(updated_source)
except SyntaxError as e:
    raise SyntaxError(
        f"Updated code has invalid syntax at line "
        f"{e.lineno}: {e.msg}. Original file not modified."
    ) from e


# Ensure both functions exist exactly once at module level.
updated_functions = [
    node.name
    for node in updated_tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
]

for function_name in required_functions:
    if updated_functions.count(function_name) != 1:
        raise ValueError(
            f"Validation failed: {function_name} must exist "
            "exactly once at module level. File not modified."
        )


# ============================================================
# 5. BACKUP AND SAVE
# ============================================================

backup_path = app_path.with_suffix(".py.bak")

# Create the backup before changing the original file.
original_source = app_path.read_text(encoding="utf-8")

backup_path.write_text(
    original_source,
    encoding="utf-8",
)

# Write only after all syntax and function checks pass.
app_path.write_text(
    updated_source,
    encoding="utf-8",
)

print("SUCCESS: Updated generate_interview_qa().")
print("SUCCESS: Updated render_interview().")
print("Standard questions: 1–15.")
print("Advanced questions: 16–20.")
print("TXT and PDF exports include all loaded questions.")
print("Python syntax validation passed.")
print(f"Updated file: {app_path.resolve()}")
print(f"Original backup: {backup_path.resolve()}")


# In[85]:


from pathlib import Path
import ast
import re
import json

app_path = Path("github_project_lab.py")

if not app_path.exists():
    raise FileNotFoundError("github_project_lab.py was not found.")

source = app_path.read_text(encoding="utf-8")


def replace_between(source, start_marker, end_marker, replacement):
    start = source.find(start_marker)
    if start == -1:
        raise ValueError(f"Could not find: {start_marker}")

    end = source.find(end_marker, start)
    if end == -1:
        raise ValueError(f"Could not find: {end_marker}")

    return source[:start] + replacement.rstrip() + "\n\n\n" + source[end:]


# ------------------------------------------------------------
# 1. More robust JSON parsing + JSON-mode AI helper
# ------------------------------------------------------------

json_helpers = r'''
def extract_json(text):
    """
    Parse model-generated JSON despite common formatting issues:
    Markdown fences, explanatory text, and trailing commas.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("The AI returned an empty response.")

    cleaned = text.strip()
    cleaned = cleaned.replace("\u201c", '"').replace("\u201d", '"')
    cleaned = cleaned.replace("\u2018", "'").replace("\u2019", "'")

    # Remove common Markdown fences.
    cleaned = re.sub(
        r"^\s*```(?:json|JSON)?\s*", "", cleaned
    )
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)

    # First try the complete response.
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try decoding a JSON object embedded in surrounding text.
    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[index:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    # Last safe repair: remove commas directly before closing braces/brackets.
    repaired = re.sub(r",\s*([}\]])", r"\1", cleaned)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError as exc:
        preview = cleaned[:350].replace("\n", " ")
        raise ValueError(
            "The AI response was not valid JSON after cleanup. "
            f"Response preview: {preview}"
        ) from exc


def ask_ai_json(prompt, system, max_tokens=2200, temperature=0.1):
    """
    Prefer Groq JSON mode. If the selected model/API does not support it,
    fall back to a regular completion; the parser and retry logic still apply.
    """
    client = get_client()

    common = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        response = client.chat.completions.create(
            **common,
            response_format={"type": "json_object"},
        )
    except Exception:
        # Compatibility fallback if JSON mode is unsupported.
        response = client.chat.completions.create(**common)

    result = response.choices[0].message.content
    if not result:
        raise ValueError("The AI returned an empty response.")
    return result.strip()
'''

source = replace_between(
    source,
    "def extract_json(text):",
    "# ============================================================\n# GITHUB REPOSITORY FUNCTIONS",
    json_helpers
)


# ------------------------------------------------------------
# 2. Replace quiz generation with validation + one retry


def prepare_file_context(path, content, max_chars=5500):
    """Prepare a file excerpt for AI-based quiz generation."""
    header = f"FILE: {path}\n\n"
    available_chars = max(0, max_chars - len(header))
    return header + content[:available_chars]



# ------------------------------------------------------------

quiz_function = r'''
def generate_quiz(repo, path, content):
    compact_content = prepare_file_context(
        path, content, max_chars=5500
    )

    system = (
        "You are a precise assessment generator. "
        "Return exactly one valid JSON object and nothing else. "
        "Do not use Markdown fences or explanatory text outside JSON."
    )

    prompt = f"""
Generate exactly 10 multiple-choice questions about this file.

Repository: {repo['owner']}/{repo['name']}
File: {path}
File type: {file_kind(path)}

Make every question specific to the supplied content.
- Python: actual functions, variables, logic, imports, and data flow.
- SQL: actual queries, joins, filters, grouping, and aggregations.
- Dataset: actual columns and supplied sample values.
- README/config: documented setup and project behavior.
- Do not invent facts that are absent from the content.
- Four distinct options per question.
- Exactly one correct option.
- The answer must be an integer from 0 to 3.
- Keep explanations to one sentence.

Output this exact JSON structure:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": 0,
      "explanation": "Short explanation"
    }}
  ]
}}

Do not include any other keys or text.

FILE CONTENT:
{compact_content}
"""

    last_error = None

    for attempt in range(2):
        try:
            current_prompt = prompt

            if attempt == 1:
                current_prompt += """

IMPORTANT RETRY:
Your previous response could not be parsed or validated.
Return a complete, syntactically valid JSON object only.
Use double quotes for all JSON keys and strings.
Do not add Markdown fences, comments, or trailing commas.
Return exactly 10 questions.
"""

            raw = ask_ai_json(
                current_prompt,
                system=system,
                max_tokens=2200,
                temperature=0.0,
            )

            data = extract_json(raw)
            questions = data.get("questions")

            if not isinstance(questions, list) or len(questions) != 10:
                raise ValueError(
                    "The response must contain exactly 10 questions."
                )

            validated = []
            for number, question in enumerate(questions, start=1):
                if not isinstance(question, dict):
                    raise ValueError(f"Question {number} is not an object.")

                q_text = question.get("question")
                options = question.get("options")
                answer = question.get("answer")
                explanation = question.get("explanation", "")

                if not isinstance(q_text, str) or not q_text.strip():
                    raise ValueError(f"Question {number} has no question text.")

                if (
                    not isinstance(options, list)
                    or len(options) != 4
                    or not all(isinstance(opt, str) and opt.strip()
                               for opt in options)
                ):
                    raise ValueError(
                        f"Question {number} must have four text options."
                    )

                # bool is a subclass of int in Python, so exclude it explicitly.
                if (
                    isinstance(answer, bool)
                    or not isinstance(answer, int)
                    or answer not in range(4)
                ):
                    raise ValueError(
                        f"Question {number} has an invalid answer index."
                    )

                validated.append({
                    "question": q_text.strip(),
                    "options": options,
                    "answer": answer,
                    "explanation": str(explanation).strip(),
                })

            return validated

        except Exception as exc:
            last_error = exc

    raise ValueError(
        "Could not generate a valid 10-question assessment after two attempts. "
        "Please try again. Technical detail: " + str(last_error)
    )
'''

source = replace_between(
    source,
    "def generate_quiz(repo, path, content):",
    "def generate_interview_qa(repo):",
    quiz_function
)


# ------------------------------------------------------------
# 3. Syntax-check before saving
# ------------------------------------------------------------

ast.parse(source)
app_path.write_text(source, encoding="utf-8")

print("✅ Quiz generation updated.")
print("✅ Robust JSON parsing added.")
print("✅ Groq JSON mode is attempted when supported.")
print("✅ Quiz validation and one automatic retry added.")
print("✅ Python syntax check passed.")


# In[86]:


from pathlib import Path
import ast

app_path = Path("github_project_lab.py")
source = app_path.read_text(encoding="utf-8")

if "def prepare_file_context(" not in source:
    marker = "def generate_quiz(repo, path, content):"

    if marker not in source:
        raise ValueError("Could not find generate_quiz() in the file.")

    helper = '''def prepare_file_context(path, content, max_chars=5500):
    """Prepare a file excerpt for AI-based quiz generation."""
    header = f"FILE: {path}\\n\\n"
    available_chars = max(0, max_chars - len(header))
    return header + content[:available_chars]


'''

    source = source.replace(marker, helper + marker, 1)

    # Verify syntax before saving.
    ast.parse(source)
    app_path.write_text(source, encoding="utf-8")
    print("Fixed: prepare_file_context() added.")
else:
    print("prepare_file_context() already exists.")

ast.parse(app_path.read_text(encoding="utf-8"))
print("Python syntax check passed.")


# In[87]:


from pathlib import Path
import ast

app_path = Path("github_project_lab.py")
source = app_path.read_text(encoding="utf-8")

# 1. Add a reusable repository-loading bar to the Home page.
marker = "# ============================================================\n# MAIN APPLICATION"

new_function = '''
def render_load_repo():
    """Allow the user to switch repositories without restarting the app."""
    st.markdown("## 🔗 Load GitHub Repo")
    st.write(
        "Finished exploring this repository? Enter another GitHub URL "
        "below to start learning a new project."
    )

    with st.form("load_another_repo_form", clear_on_submit=False):
        new_repo_url = st.text_input(
            "GitHub repository URL",
            value=st.session_state.repo_url,
            placeholder="https://github.com/owner/repository",
            key="load_another_repo_url",
        )
        submitted = st.form_submit_button(
            "🚀 Load GitHub Repo",
            use_container_width=True,
        )

    if submitted:
        try:
            parse_github_url(new_repo_url)

            with st.spinner("Loading your new GitHub repository..."):
                loaded = load_repository(new_repo_url)

            # Replace the current repository only after the new one loads.
            st.session_state.repo_url = new_repo_url.strip()
            st.session_state.repo = loaded
            st.session_state.files = loaded["files"]
            st.session_state.tree = loaded["tree"]
            st.session_state.readme = loaded["readme"]

            # Clear learning progress from the previous repository.
            st.session_state.selected_file = None
            st.session_state.explanations = {}
            st.session_state.quizzes = {}
            st.session_state.answers = {}
            st.session_state.submitted = {}
            st.session_state.interview_qa = None
            st.session_state.repo_error = None
            st.session_state.page = "Home"

            st.success(
                f"Successfully loaded {loaded['owner']}/{loaded['name']}!"
            )
            st.rerun()

        except Exception as e:
            st.error(f"Could not load the new repository: {e}")


'''

if "def render_load_repo():" not in source:
    if marker not in source:
        raise ValueError("Could not find the MAIN APPLICATION section.")
    source = source.replace(marker, new_function + marker, 1)

# 2. Display the new bar on the Home page.
home_marker = '''if st.session_state.page == "Home":
    render_repo_overview(repo)
    render_file_explorer(repo)
'''

home_replacement = '''if st.session_state.page == "Home":
    render_load_repo()
    st.markdown("---")
    render_repo_overview(repo)
    render_file_explorer(repo)
'''

if home_marker in source:
    source = source.replace(home_marker, home_replacement, 1)
elif home_replacement not in source:
    raise ValueError(
        "Could not find the expected Home-page code. "
        "No Home-page changes were applied."
    )

# Validate syntax before saving.
ast.parse(source)
app_path.write_text(source, encoding="utf-8")

print("✅ Added the Load GitHub Repo section to Home.")
print("✅ Added repository switching without notebook reruns.")
print("✅ Previous repository learning progress resets on successful switch.")
print("✅ Python syntax check passed.")


# In[88]:


from pathlib import Path
import ast

path = Path("github_project_lab.py")
source = path.read_text(encoding="utf-8")

helper = '''

def limit_repo_context(repo, max_chars=10000):
    """Return a size-limited repository context for AI prompts."""
    context = make_repo_context(repo)

    if not isinstance(context, str):
        context = str(context)

    if len(context) > max_chars:
        context = context[:max_chars] + (
            "\\n\\n[Repository context truncated to fit the request.]"
        )

    return context

'''

if "def limit_repo_context(" not in source:
    marker = "def make_repo_context("
    if marker in source:
        source = source.replace(marker, helper + "\n\n" + marker, 1)
    else:
        raise ValueError(
            "Could not find make_repo_context(). "
            "Please share that function so I can place the helper correctly."
        )

ast.parse(source)
path.write_text(source, encoding="utf-8")

print("Added limit_repo_context successfully.")


# In[89]:


from getpass import getpass
from pathlib import Path
import os
import sys
import time
import socket
import subprocess
import webbrowser

APP_FILE = Path("github_project_lab.py").resolve()

if not APP_FILE.exists():
    raise FileNotFoundError(
        f"Could not find {APP_FILE}\n"
        "Run the cell that creates github_project_lab.py first."
    )

# Enter your Groq key privately; it won't be displayed as you type.
groq_key = getpass("Enter your Groq API key: ").strip()

if not groq_key:
    raise ValueError("The Groq API key cannot be empty.")

# Pick an available local port.
def port_is_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0

PORT = next((p for p in range(8501, 8511) if port_is_available(p)), None)

if PORT is None:
    raise RuntimeError("Ports 8501–8510 are busy. Stop an existing Streamlit app and retry.")

# Pass the key to this child process only. The app reads it from its environment.
env = os.environ.copy()
env["GROQ_API_KEY"] = groq_key

# Optional: set a different supported Groq model here if needed.
# env["GROQ_MODEL"] = "openai/gpt-oss-20b"

log_path = Path("github_project_lab.log").resolve()
log_file = open(log_path, "w", encoding="utf-8")

process = subprocess.Popen(
    [
        sys.executable, "-m", "streamlit", "run", str(APP_FILE),
        "--server.port", str(PORT),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ],
    env=env,
    cwd=str(APP_FILE.parent),
    stdout=log_file,
    stderr=subprocess.STDOUT,
)

# Keep references available in the notebook.
streamlit_process = process
streamlit_log_file = log_file
streamlit_log_path = log_path

url = f"http://localhost:{PORT}"

print("RepoRiot is starting.")
print(f"App URL: {url}")
print(f"Log file: {log_path}")
print("If the page doesn't open automatically, copy the App URL into your browser.")

time.sleep(3)
webbrowser.open(url)


# In[81]:


streamlit_process.terminate()
streamlit_process.wait(timeout=10)


# In[90]:


get_ipython().run_cell_magic('writefile', 'requirements.txt', 'streamlit\nrequests\ngroq\nreportlab\n')


# In[91]:


from pathlib import Path

path = Path("requirements.txt")

print("File exists:", path.exists())
print(path.read_text() if path.exists() else "File not found")


# In[ ]:




