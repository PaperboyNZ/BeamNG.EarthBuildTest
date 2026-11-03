"""Source inputs shared by development cache keys and packaged CODE_ID."""
from pathlib import Path


def source_files(server_dir):
    """Sorted relative paths; exclude tests, bytecode and generated outputs."""
    root = Path(server_dir)
    paths = list(root.glob("*.py"))
    # Climate now participates in v2 architecture planning as well as ambience.
    # Cover both development keys and packaged CODE_ID with the actual asset.
    paths.extend(root.glob("koppen_1991_2020_0p1.png"))
    for name in ("buildgen", "sitegen"):
        package = root / name
        if package.is_dir():
            paths.extend(p for p in package.rglob("*")
                         if p.is_file() and p.suffix in (".py", ".json") and "__pycache__" not in p.parts)
    return sorted(p.relative_to(root).as_posix() for p in paths)
