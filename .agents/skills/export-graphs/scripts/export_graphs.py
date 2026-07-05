#!/usr/bin/env python3
"""
通用 LangGraph 图导出引擎（脚本型 skill 的执行内核）。

设计原则（沿用本仓库 201/docs/export_graphs.py 已验证的做法）：
- draw_mermaid_png() 只需要图的「拓扑结构」（节点 + 边），不会执行任何节点，
  因此 builder 模块应当用「桩节点」重建拓扑，绝不调用 LLM / 联网，零 API 费用。
- 联网渲染（mermaid.ink）失败时，自动回退导出 .mmd 源码，保证离线可用。

用法：
    python3 export_graphs.py <builder.py> [out_dir] [--xray]

<builder.py> 是一个「桩重建」模块。本引擎导入它（执行其顶层代码，由该模块
自行完成 sys.path 注入），然后按以下优先级发现要导出的编译图：
  1. build_exports() 函数 -> 返回 {文件名: graph 或 (graph, xray)}
  2. EXPORTS 字典         -> {文件名: graph 或 (graph, xray)}
  3. 模块级编译图变量      -> 变量名即文件名（graph_foo -> graph_foo.png）

out_dir 缺省为 <builder.py 所在目录>/image。
--xray 对所有图强制展开子图（覆盖各自的 xray 设置）。
"""
import argparse
import importlib.util
import sys
from pathlib import Path


def load_module(path: str):
    """按文件路径导入模块；其顶层代码会运行（含 sys.path 注入、桩图构建）。"""
    file = Path(path).resolve()
    if not file.exists():
        print(f"找不到 builder 文件：{file}", file=sys.stderr)
        sys.exit(1)
    spec = importlib.util.spec_from_file_location(file.stem, file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def is_compiled_graph(obj) -> bool:
    """鸭子判定：编译后的 LangGraph 图都有可调用的 get_graph()。"""
    return callable(getattr(obj, "get_graph", None))


def collect_exports(mod) -> dict:
    """按优先级发现要导出的图。"""
    if callable(getattr(mod, "build_exports", None)):
        return dict(mod.build_exports())
    if isinstance(getattr(mod, "EXPORTS", None), dict):
        return dict(mod.EXPORTS)
    found = {}
    for name, obj in vars(mod).items():
        if not name.startswith("_") and is_compiled_graph(obj):
            found[name] = obj
    return found


def normalize(entry):
    """entry 可为 graph，或 (graph, xray)。"""
    if isinstance(entry, (tuple, list)):
        graph = entry[0]
        xray = entry[1] if len(entry) > 1 else False
        return graph, bool(xray)
    return entry, False


def export_one(graph, out_dir: Path, filename: str, xray: bool):
    out_dir.mkdir(parents=True, exist_ok=True)
    if not filename.endswith(".png"):
        filename += ".png"
    path = out_dir / filename
    try:
        png = graph.get_graph(xray=xray).draw_mermaid_png()
        path.write_bytes(png)
        print(f"[OK]  {path}  ({len(png)} bytes)")
    except Exception as e:
        # 离线时 mermaid.ink 不可用，回退导出 .mmd 源码
        mmd = graph.get_graph(xray=xray).draw_mermaid()
        mmd_path = path.with_suffix(".mmd")
        mmd_path.write_text(mmd, encoding="utf-8")
        print(f"[FALLBACK] PNG 失败 ({type(e).__name__}: {e})，已导出源码: {mmd_path}")


def main():
    ap = argparse.ArgumentParser(description="通用 LangGraph 图导出引擎")
    ap.add_argument("builder", help="桩重建模块 .py 路径")
    ap.add_argument("out_dir", nargs="?", default=None, help="输出目录，缺省为 builder 同级 image/")
    ap.add_argument("--xray", action="store_true", help="对所有图强制展开子图")
    args = ap.parse_args()

    mod = load_module(args.builder)
    exports = collect_exports(mod)
    if not exports:
        print(
            "未发现可导出的编译图。请在 builder 模块中提供 build_exports()、"
            "EXPORTS 字典，或在模块级暴露已编译的图变量。",
            file=sys.stderr,
        )
        sys.exit(1)

    out_dir = Path(args.out_dir) if args.out_dir else Path(args.builder).resolve().parent / "image"
    for filename, entry in exports.items():
        graph, xray = normalize(entry)
        export_one(graph, out_dir, filename, args.xray or xray)
    print("完成。")


if __name__ == "__main__":
    main()
