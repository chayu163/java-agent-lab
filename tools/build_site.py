"""构建 docs/ 站点的内容层：笔记、代码、调研文档。

运行：uv run --group docs python tools/build_site.py

产物全部写进 docs/content/（该目录是生成物，不入库）：
    manifest.json          站点索引，前端据此知道有哪些笔记和代码
    notes/<day>/<slug>.html   渲染好的笔记片段
    code/<day>/<name>.html    高亮好的代码片段
    research/<slug>.html      调研与计划文档
"""

from __future__ import annotations

import html
import json
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline
from markdown_it.token import Token

ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = ROOT / "notes"
DOCS_DIR = ROOT / "docs"
CONTENT_DIR = DOCS_DIR / "content"
RESEARCH_DIR = ROOT / "research"

CALLOUT_TITLES = {
	"note": "笔记",
	"abstract": "摘要",
	"summary": "摘要",
	"tldr": "摘要",
	"info": "说明",
	"todo": "待办",
	"tip": "提示",
	"hint": "提示",
	"important": "重要",
	"success": "完成",
	"check": "完成",
	"done": "完成",
	"question": "问题",
	"help": "问题",
	"faq": "问题",
	"warning": "警告",
	"caution": "警告",
	"attention": "警告",
	"failure": "失败",
	"fail": "失败",
	"missing": "缺失",
	"danger": "危险",
	"error": "危险",
	"bug": "缺陷",
	"example": "示例",
	"quote": "引用",
	"cite": "引用",
}

CALLOUT_ICONS = {
	"note": "✎", "abstract": "≡", "summary": "≡", "tldr": "≡",
	"info": "i", "todo": "☑", "tip": "✦", "hint": "✦", "important": "!",
	"success": "✓", "check": "✓", "done": "✓", "question": "?",
	"help": "?", "faq": "?", "warning": "⚠", "caution": "⚠",
	"attention": "⚠", "failure": "✕", "fail": "✕", "missing": "✕",
	"danger": "⚡", "error": "⚡", "bug": "✹", "example": "▸", "quote": "❝",
	"cite": "❝",
}

CALLOUT_RE = re.compile(r"^\[!(\w+)\]([+-]?)\s*(.*)$")
TASK_RE = re.compile(r"^\[([ xX])\]\s+")
FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)

PY_KEYWORDS = {
	"False", "None", "True", "and", "as", "assert", "async", "await", "break",
	"class", "continue", "def", "del", "elif", "else", "except", "finally",
	"for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal",
	"not", "or", "pass", "raise", "return", "try", "while", "with", "yield",
	"self", "cls", "match", "case",
}

JAVA_KEYWORDS = {
	"abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
	"class", "const", "continue", "default", "do", "double", "else", "enum",
	"extends", "final", "finally", "float", "for", "goto", "if", "implements",
	"import", "instanceof", "int", "interface", "long", "native", "new",
	"package", "private", "protected", "public", "return", "short", "static",
	"strictfp", "super", "switch", "synchronized", "this", "throw", "throws",
	"transient", "try", "void", "volatile", "while", "record", "var", "yield",
	"true", "false", "null",
}


# --------------------------------------------------------------------------
# frontmatter
# --------------------------------------------------------------------------


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
	"""拆出 YAML frontmatter 的常用键，剩余正文原样返回。

	只认笔记里实际用到的形状：`key: value`、`key:` + `- item` 列表。
	"""
	match = FRONTMATTER_RE.match(text)
	if not match:
		return {}, text

	meta: dict[str, Any] = {}
	current_key: str | None = None
	for raw in match.group(1).splitlines():
		line = raw.rstrip()
		if not line.strip():
			continue
		if line.lstrip().startswith("- ") and current_key:
			value = line.lstrip()[2:].strip()
			if not isinstance(meta.get(current_key), list):
				meta[current_key] = []
			meta[current_key].append(value)
			continue
		if ":" in line:
			key, _, value = line.partition(":")
			key = key.strip()
			value = value.strip()
			if value:
				meta[key] = value
				current_key = None
			else:
				current_key = key
				meta[key] = []
	return meta, text[match.end():]


# --------------------------------------------------------------------------
# markdown 渲染
# --------------------------------------------------------------------------


def slugify_heading(text: str) -> str:
	"""把标题转成锚点，规则和 Obsidian 大致对齐。"""
	slug = re.sub(r"[`*_~\[\]()#>]", "", text).strip()
	slug = re.sub(r"[\s：:，,。、·/]+", "-", slug)
	return slug.strip("-").lower()


def wikilink_rule(state: StateInline, silent: bool) -> bool:
	"""解析 [[目标]] 与 [[目标|别名]]。"""
	src, pos = state.src, state.pos
	if src[pos:pos + 2] != "[[":
		return False
	end = src.find("]]", pos + 2)
	if end < 0:
		return False
	inner = src[pos + 2:end]
	if not inner or "\n" in inner or len(inner) > 200:
		return False
	if not silent:
		target, _, alias = inner.partition("|")
		token = state.push("wikilink", "", 0)
		token.content = inner
		token.meta = {"target": target.strip(), "alias": alias.strip()}
	state.pos = end + 2
	return True


def make_markdown() -> MarkdownIt:
	md = MarkdownIt("gfm-like", {"html": False, "linkify": False})
	md.inline.ruler.before("link", "wikilink", wikilink_rule)
	md.add_render_rule("wikilink", render_wikilink)
	return md


def render_wikilink(renderer: Any, tokens: list[Token], idx: int, options: Any, env: Any) -> str:
	token = tokens[idx]
	target = token.meta.get("target", "")
	alias = token.meta.get("alias", "")
	label = alias or target
	anchor = env.get("anchor_index", {}).get(normalize_ref(target))
	if anchor:
		return f'<a class="wikilink" href="#{html.escape(anchor)}">{html.escape(label)}</a>'
	if target.startswith("http"):
		return f'<a class="wikilink" href="{html.escape(target)}">{html.escape(label)}</a>'
	return f'<span class="wikilink is-unresolved" title="暂无对应内容">{html.escape(label)}</span>'


def normalize_ref(text: str) -> str:
	return re.sub(r"[\s：:，,。、·/#\-\|「」『』（）()]+", "", text).lower()


def find_matching(tokens: list[Token], start: int, kind: str) -> int:
	depth = 0
	for i in range(start, len(tokens)):
		if tokens[i].type == f"{kind}_open":
			depth += 1
		elif tokens[i].type == f"{kind}_close":
			depth -= 1
			if depth == 0:
				return i
	return len(tokens) - 1


def detect_callout(inner: list[Token], md: MarkdownIt) -> tuple[str, str, list[Token]] | None:
	if len(inner) < 2 or inner[0].type != "paragraph_open" or inner[1].type != "inline":
		return None
	first_line, _, remainder = inner[1].content.partition("\n")
	match = CALLOUT_RE.match(first_line.strip())
	if not match:
		return None

	kind = match.group(1).lower()
	title = match.group(3).strip() or CALLOUT_TITLES.get(kind, kind)

	body_tokens = list(inner)
	if remainder.strip():
		# 首段去掉标记行后要重新解析，否则 children 里还留着 "[!note]" 文本
		inline = body_tokens[1]
		inline.content = remainder
		reparsed = md.parseInline(remainder, {})
		inline.children = reparsed[0].children if reparsed else []
	else:
		body_tokens = body_tokens[3:]
	return kind, title, body_tokens


def render_tokens(tokens: list[Token], md: MarkdownIt, env: dict[str, Any]) -> str:
	out: list[str] = []
	i = 0
	while i < len(tokens):
		token = tokens[i]

		if token.type == "blockquote_open":
			close = find_matching(tokens, i, "blockquote")
			inner = tokens[i + 1:close]
			callout = detect_callout(inner, md)
			if callout:
				kind, title, body_tokens = callout
				icon = CALLOUT_ICONS.get(kind, "•")
				body = render_tokens(body_tokens, md, env)
				out.append(
					f'<div class="callout callout-{html.escape(kind)}">'
					f'<div class="callout-head"><span class="callout-icon">{icon}</span>'
					f'<span class="callout-title">{html.escape(title)}</span></div>'
					f'<div class="callout-body">{body}</div></div>'
				)
			else:
				body = render_tokens(inner, md, env)
				out.append(f"<blockquote>{body}</blockquote>")
			i = close + 1
			continue

		if token.type in ("blockquote_close",):
			i += 1
			continue

		out.append(md.renderer.render([token], md.options, env))
		i += 1

	return "".join(out)


def apply_task_lists(tokens: list[Token]) -> None:
	"""把 `- [x] 项` 变成带勾选样式的列表项。"""
	for i, token in enumerate(tokens):
		if token.type != "list_item_open":
			continue
		if i + 2 >= len(tokens):
			continue
		if tokens[i + 1].type != "paragraph_open" or tokens[i + 2].type != "inline":
			continue
		inline = tokens[i + 2]
		match = TASK_RE.match(inline.content)
		if not match:
			continue
		checked = match.group(1).lower() == "x"
		inline.content = inline.content[match.end():]
		if inline.children and inline.children[0].type == "text":
			inline.children[0].content = inline.children[0].content[match.end():]
		token.attrSet("class", f"task-item {'is-done' if checked else 'is-open'}")


def add_heading_ids(tokens: list[Token]) -> dict[str, str]:
	"""给标题加 id，并返回 归一化标题 -> 锚点 的索引。"""
	index: dict[str, str] = {}
	for i, token in enumerate(tokens):
		if token.type != "heading_open":
			continue
		if i + 1 >= len(tokens) or tokens[i + 1].type != "inline":
			continue
		text = tokens[i + 1].content
		slug = slugify_heading(text)
		if not slug:
			continue
		token.attrSet("id", slug)
		index[normalize_ref(text)] = slug
	return index


def render_markdown(text: str) -> tuple[dict[str, Any], str]:
	meta, body = split_frontmatter(text)
	md = make_markdown()

	tokens = md.parse(body, {})
	apply_task_lists(tokens)
	anchor_index = add_heading_ids(tokens)

	env: dict[str, Any] = {"anchor_index": anchor_index}
	return meta, render_tokens(tokens, md, env)


# --------------------------------------------------------------------------
# 代码高亮
# --------------------------------------------------------------------------

TOKEN_RE = re.compile(
	r"(?P<comment>#[^\n]*|//[^\n]*|/\*[\s\S]*?\*/)"
	r"|(?P<string>\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*')"
	r"|(?P<number>\b0[xX][0-9a-fA-F]+\b|\b\d+(?:\.\d+)?\b)"
	r"|(?P<word>[A-Za-z_]\w*)"
)


def highlight(code: str, lang: str) -> str:
	keywords = PY_KEYWORDS if lang == "python" else JAVA_KEYWORDS
	out: list[str] = []
	pos = 0
	for match in TOKEN_RE.finditer(code):
		out.append(html.escape(code[pos:match.start()]))
		pos = match.end()
		value = match.group(0)
		escaped = html.escape(value)
		if match.lastgroup == "comment":
			out.append(f'<span class="tok-comment">{escaped}</span>')
		elif match.lastgroup == "string":
			out.append(f'<span class="tok-string">{escaped}</span>')
		elif match.lastgroup == "number":
			out.append(f'<span class="tok-number">{escaped}</span>')
		elif match.lastgroup == "word" and value in keywords:
			out.append(f'<span class="tok-keyword">{escaped}</span>')
		else:
			out.append(escaped)
	out.append(html.escape(code[pos:]))
	return "".join(out)


def code_lang(path: Path) -> str:
	return {".py": "python", ".java": "java"}.get(path.suffix, "text")


# --------------------------------------------------------------------------
# 内容收集
# --------------------------------------------------------------------------


def reset_content_dir() -> None:
	if CONTENT_DIR.exists():
		shutil.rmtree(CONTENT_DIR)
	(CONTENT_DIR / "notes").mkdir(parents=True)
	(CONTENT_DIR / "code").mkdir(parents=True)
	(CONTENT_DIR / "research").mkdir(parents=True)


def build_notes(manifest: dict[str, Any]) -> None:
	for path in sorted(NOTES_DIR.glob("day*/*.md")):
		day = path.parent.name
		meta, rendered = render_markdown(path.read_text(encoding="utf-8"))
		target_dir = CONTENT_DIR / "notes" / day
		target_dir.mkdir(parents=True, exist_ok=True)
		(target_dir / f"{path.stem}.html").write_text(rendered, encoding="utf-8")
		manifest["notes"].append({
			"day": day,
			"slug": f"{day}/{path.stem}",
			"title": meta.get("title") or path.stem,
			"date": meta.get("date", ""),
			"phase": meta.get("phase", ""),
			"status": meta.get("status", ""),
			"tags": meta.get("tags", []),
			"path": f"notes/{day}/{path.stem}.html",
		})


def build_code(manifest: dict[str, Any]) -> None:
	for day_dir in sorted(ROOT.glob("day*")):
		if not day_dir.is_dir():
			continue
		day = day_dir.name
		for sub in ("python", "java"):
			for path in sorted((day_dir / sub).glob("*")):
				if path.suffix not in (".py", ".java"):
					continue
				lang = code_lang(path)
				rendered = (
					f'<pre class="code-block" data-lang="{lang}"><code>'
					f"{highlight(path.read_text(encoding='utf-8'), lang)}</code></pre>"
				)
				target_dir = CONTENT_DIR / "code" / day
				target_dir.mkdir(parents=True, exist_ok=True)
				out_name = f"{sub}-{path.stem}.html"
				(target_dir / out_name).write_text(rendered, encoding="utf-8")
				manifest["code"].append({
					"day": day,
					"name": path.name,
					"dir": sub,
					"lang": lang,
					"lines": len(path.read_text(encoding="utf-8").splitlines()),
					"path": f"code/{day}/{out_name}",
				})


def build_research(manifest: dict[str, Any]) -> None:
	for path in sorted(RESEARCH_DIR.rglob("*.md")):
		meta, rendered = render_markdown(path.read_text(encoding="utf-8"))
		slug = re.sub(r"[^\w一-鿿-]+", "-", path.stem).strip("-")
		(CONTENT_DIR / "research" / f"{slug}.html").write_text(rendered, encoding="utf-8")
		first_heading = re.search(r"^#\s+(.+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
		manifest["research"].append({
			"slug": slug,
			"title": meta.get("title") or (first_heading.group(1).strip() if first_heading else path.stem),
			"group": path.parent.name,
			"path": f"research/{slug}.html",
		})


def main() -> None:
	reset_content_dir()
	manifest: dict[str, Any] = {
		"generatedAt": date.today().isoformat(),
		"notes": [],
		"code": [],
		"research": [],
	}
	build_notes(manifest)
	build_code(manifest)
	build_research(manifest)
	(CONTENT_DIR / "manifest.json").write_text(
		json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
	)
	print(
		f"notes={len(manifest['notes'])} code={len(manifest['code'])} "
		f"research={len(manifest['research'])} -> {CONTENT_DIR.relative_to(ROOT)}"
	)


if __name__ == "__main__":
	main()
