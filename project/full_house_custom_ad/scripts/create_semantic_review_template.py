#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def file_hash(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def review_path_from_config(config: dict[str, Any], output_name: str, explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        return path if path.is_absolute() else ROOT / path
    configured = config.get("manual_semantic_review_file")
    if isinstance(configured, str) and configured.strip():
        path = Path(configured)
        return path if path.is_absolute() else ROOT / path
    return OUT_DIR / f"{output_name}_semantic_review.md"


def write_template(path: Path, config: dict[str, Any], reviewer: str, overwrite: bool) -> None:
    project_id = str(config.get("project_id", ""))
    output_name = str(config.get("output_name", project_id or "walkthrough"))
    source_video = resolve_path(config.get("source_video"))
    continuity_report = OUT_DIR / f"{output_name}_continuity_report.md"
    if path.exists() and not overwrite:
        raise SystemExit(f"复核文件已存在：{path}\n如需覆盖，请加 --overwrite。")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""# 样片级连续空间漫游人工语义复核

项目 ID：{project_id}
源视频：{source_video or ''}
源视频 hash：{file_hash(source_video)}
continuity report：{continuity_report}
复核日期：{date.today().isoformat()}
人工复核人：{reviewer}

## 样片级专项评分

样片级专项评分：___ / 100

## 逐项复核

请把符合项勾选为 `[x]`。L4 最终通过必须全部满足：样片级专项评分不低于 85 分，一致性项目选“是”，“是否存在明显换房”选“否”，结论选“通过”。

- 电视墙是否一致：[ ] 是 [ ] 否
- 沙发是否一致：[ ] 是 [ ] 否
- 餐桌是否一致：[ ] 是 [ ] 否
- 地面材质是否一致：[ ] 是 [ ] 否
- 柜体颜色是否一致：[ ] 是 [ ] 否
- 灯光色温是否一致：[ ] 是 [ ] 否
- 空间比例是否一致：[ ] 是 [ ] 否
- 镜头路径是否连续：[ ] 是 [ ] 否
- 是否存在明显换房：[ ] 否 [ ] 是
- 是否达到样片发布级：[ ] 是 [ ] 否

## 结论

复核结论：[ ] 通过 [ ] 不通过

备注：
""",
        encoding="utf-8",
    )
    print(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a semantic review template for L4 sample-level walkthrough approval.")
    parser.add_argument("--config", required=True, help="Project JSON config")
    parser.add_argument("--output", help="Output semantic review markdown path")
    parser.add_argument("--reviewer", default="", help="Manual reviewer name")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    project_id = str(config.get("project_id", config_path.parent.name))
    output_name = str(config.get("output_name", project_id))
    path = review_path_from_config(config, output_name, args.output)
    write_template(path, config, args.reviewer, args.overwrite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
