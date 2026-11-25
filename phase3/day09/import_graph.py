"""Day 9 练习：解析 OpenManus 的 app 内部导入，输出子包级依赖边。

用法：uv run phase3/day09/import_graph.py <仓库路径>
用 ast 只解析 `from app.… import …` 与 `import app.…` 两种语句，
把模块路径归并到 app 的顶层子包，不执行目标仓库的任何代码。
"""

from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path


def module_of(node: ast.Import | ast.ImportFrom) -> str | None:
    """返回该 import 语句引用的 app 模块路径；非 app 导入返回 None。

    `from app.schema import Message` 取 `app.schema`；
    `import app.agent.base` 取 `app.agent.base`。
    """
    if isinstance(node, ast.ImportFrom) and node.module:
        return node.module if node.module.startswith("app") else None
    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name.startswith("app"):
                return alias.name
    return None


def parse_edges(repo_root: Path) -> tuple[dict[str, set[str]], list[str]]:
    """解析 app/ 下全部源码，返回 ({源子包: {目标子包, …}}, 解析失败的文件列表)。

    `app/` 顶层文件（如 schema.py）归入 "(top)"，目录归入各自名字；
    目标模块取第二段：app.agent.toolcall → agent，app.schema → (top)。
    目标仓库要求 Python 3.12，本练习运行在 3.11 上：PEP 701 之前的语法
    禁止 f-string 表达式内出现反斜杠，这类文件会 SyntaxError，
    记入 unparsed 并继续，不让单文件中断全量统计。
    """
    app_dir = repo_root / "app"
    if not app_dir.is_dir():
        raise ValueError(f"{repo_root} 下没有 app/ 目录")

    edges: dict[str, set[str]] = defaultdict(set)
    unparsed: list[str] = []
    for py_file in sorted(app_dir.rglob("*.py")):
        rel = py_file.relative_to(app_dir)
        source_pkg = "(top)" if len(rel.parts) == 1 else rel.parts[0]
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            unparsed.append(rel.as_posix())
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            target_module = module_of(node)
            if target_module is None:
                continue
            parts = target_module.split(".")
            # app.x.y → x 是子包；只有 app.x 且 x 是模块文件时也按顶层名记录，
            # 由调用方对照文件清单区分。这里统一把第二段作为目标标识。
            target_pkg = parts[1] if len(parts) > 1 else "(self)"
            if target_pkg != source_pkg:
                edges[source_pkg].add(target_pkg)
    return dict(edges), unparsed


def check_examples() -> None:
    # 断言 1：两种 import 形状都能取出模块路径；相对导入与非 app 导入返回 None。
    import ast as _ast

    from_node = _ast.parse("from app.schema import Message").body[0]
    assert isinstance(from_node, _ast.ImportFrom)
    assert module_of(from_node) == "app.schema"
    import_node = _ast.parse("import app.agent.base").body[0]
    assert isinstance(import_node, _ast.Import)
    assert module_of(import_node) == "app.agent.base"
    relative_node = _ast.parse("from .base import BaseAgent").body[0]
    assert isinstance(relative_node, _ast.ImportFrom)
    assert module_of(relative_node) is None
    plain_node = _ast.parse("import json").body[0]
    assert isinstance(plain_node, _ast.Import)
    assert module_of(plain_node) is None

    # 断言 2：跨子包的 import 产生一条边，子包内 import 不产生自边。
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pkg, other = root / "app" / "tool", root / "app" / "agent"
        pkg.mkdir(parents=True)
        other.mkdir()
        (root / "app" / "__init__.py").write_text("", encoding="utf-8")
        (root / "app" / "schema.py").write_text("X = 1\n", encoding="utf-8")
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (other / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "base.py").write_text("import json\n", encoding="utf-8")
        (other / "toolcall.py").write_text(
            "from app.tool.base import BaseTool\nfrom app.tool.collection import C\n",
            encoding="utf-8",
        )
        edges, unparsed = parse_edges(root)
        assert "agent" in edges and edges["agent"] == {"tool"}, edges
        # tool/base.py 只有标准库导入，不应产生指向 tool 的自边，也不应保留空键
        assert edges.get("tool") in (None, set()), edges
        assert unparsed == [], unparsed


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit("用法: uv run phase3/day09/import_graph.py <仓库路径>")
    repo_root = Path(sys.argv[1]).resolve()

    check_examples()
    edges, unparsed = parse_edges(repo_root)

    if unparsed:
        print(f"以下 {len(unparsed)} 个文件解析失败（本机 3.11 不支持其语法，边可能不全）：")
        for name in unparsed:
            print(f"  {name}")

    print("源子包 -> 目标子包（app 内部导入）")
    for source in sorted(edges):
        targets = ", ".join(sorted(edges[source]))
        print(f"{source:<10} -> {targets}")

    # 对照 README 分层表：tool 层不应反向依赖 agent。真实克隆命中的
    # tool -> agent 来自 chart_visualization/test/ 下的 demo 脚本（演示程序，
    # 不被 app/tool/__init__ 导入），属预期例外；依赖边按文件名逐条核对。
    if "tool" in edges and "agent" in edges["tool"]:
        print("警告: tool -> agent 存在导入边，逐文件核对来源是否为演示脚本", file=sys.stderr)
    else:
        print("tool 层未反向依赖 agent 层，与分层表一致。")


if __name__ == "__main__":
    main()
