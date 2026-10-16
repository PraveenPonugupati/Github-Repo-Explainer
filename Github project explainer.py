


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




# In[91]:


from pathlib import Path

path = Path("requirements.txt")

print("File exists:", path.exists())
print(path.read_text() if path.exists() else "File not found")


# In[ ]:




