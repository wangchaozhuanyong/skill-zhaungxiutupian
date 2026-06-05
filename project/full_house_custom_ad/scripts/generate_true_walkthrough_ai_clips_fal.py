#!/usr/bin/env python3
from __future__ import annotations

import runpy
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().with_name("generate_segmented_ai_walkthrough_clips_fal.py")


def main() -> None:
    print(
        "Deprecated: generate_true_walkthrough_ai_clips_fal.py generates multiple independent AI clips. "
        "It is now treated as L2 segmented AI walkthrough, not true walkthrough.",
        file=sys.stderr,
    )
    if "--config" not in sys.argv and "--clips-dir" not in sys.argv:
        sys.argv.extend(["--clips-dir", "ai_clips/true_walkthrough_19s"])
    sys.argv[0] = str(SCRIPT)
    runpy.run_path(str(SCRIPT), run_name="__main__")


if __name__ == "__main__":
    main()
