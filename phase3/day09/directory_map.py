"""Day 9 练习：扫描 OpenManus 仓库生成目录地图底稿。

用法：uv run phase3/day09/directory_map.py <仓库路径>
只统计 app/ 下的 .py 文件，按子包聚合文件数与行数；不导入目标仓库的代码。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict


class PackageStat(TypedDict):
    package: str
    files: int
    lines: int
    max_file: str
    max_lines: int


def scan_package(package_dir: Path) -> PackageStat:
    """统计单个子包的 Python 文件数、总行数与最大文件。

    行数按物理行计，不做代码/注释区分；`__pycache__` 等目录不含 .py 文件，
    由 rglob 的后缀过滤自然排除。
    """
    py_files = sorted(package_dir.rglob("*.py"))
    total_lines = 0
    max_name = ""
    max_lines = 0
    for py_file in py_files:
        lines = len(py_file.read_text(encoding="utf-8").splitlines())
        total_lines += lines
        if lines > max_lines:
            max_lines = lines
            max_name = py_file.relative_to(package_dir).as_posix()
    return {
        "package": package_dir.name,
        "files": len(py_files),
        "lines": total_lines,
        "max_file": max_name,
        "max_lines": max_lines,
    }


def build_map(repo_root: Path) -> list[PackageStat]:
    """返回 app/ 顶层子包与顶层单文件的统计，按行数降序排列。"""
    app_dir = repo_root / "app"
    if not app_dir.is_dir():
        raise ValueError(f"{repo_root} 下没有 app/ 目录")

    stats: list[PackageStat] = []
    top_files = 0
    top_file_lines = 0
    for entry in sorted(app_dir.iterdir()):
        if entry.is_dir() and not entry.name.startswith("__"):
            stats.append(scan_package(entry))
        elif entry.is_file() and entry.suffix == ".py":
            top_files += 1
            top_file_lines += len(entry.read_text(encoding="utf-8").splitlines())
    if top_files:
        stats.append(
            {
                "package": "(app 顶层)",
                "files": top_files,
                "lines": top_file_lines,
                "max_file": "—",
                "max_lines": 0,
            }
        )
    return sorted(stats, key=lambda stat: stat["lines"], reverse=True)


def check_examples() -> None:
    # 断言 1：rglob("*.py") 不进入 __pycache__——目录里只有 .pyc，文件数过滤后为 0。
    # 这里用一个临时目录模拟，避免练习依赖真实仓库的内容。
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "demo"
        (pkg / "__pycache__").mkdir(parents=True)
        (pkg / "__pycache__" / "compiled.pyc").write_bytes(b"")
        (pkg / "core.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
        stat = scan_package(pkg)
        assert stat["files"] == 1, stat
        assert stat["lines"] == 2, stat
        assert stat["max_file"] == "core.py", stat

    # 断言 2：app/ 缺失时报错，而不是返回空地图。
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        try:
            build_map(Path(tmp))
        except ValueError:
            pass
        else:
            raise AssertionError("缺少 app/ 目录时应抛 ValueError")


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit("用法: uv run phase3/day09/directory_map.py <仓库路径>")
    repo_root = Path(sys.argv[1]).resolve()

    check_examples()
    stats = build_map(repo_root)

    print(f"仓库: {repo_root}")
    print(f"{'包':<14}{'文件数':>6}{'行数':>8}  最大文件")
    for stat in stats:
        print(
            f"{stat['package']:<14}{stat['files']:>6}{stat['lines']:>8}  "
            f"{stat['max_file']} ({stat['max_lines']} 行)"
        )
    total = sum(stat["files"] for stat in stats)
    print(f"共 {total} 个 Python 文件。人工补充：各层职责、BaseAgent→Manus 继承链、配置流向。")


if __name__ == "__main__":
    main()
