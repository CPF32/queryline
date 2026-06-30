"""Build the bundled Python backend used by packaged desktop installers."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
BACKEND_DIST = ROOT / "backend-dist"
BACKEND_DIST_ARM64 = ROOT / "backend-dist-arm64"
BACKEND_DIST_X64 = ROOT / "backend-dist-x64"
WORK_DIR = ROOT / "build" / "pyinstaller"
SPEC_PATH = ROOT / "desktop" / "text-to-sql-backend.spec"
BACKEND_NAME = "text-to-sql-backend"


def _ensure_frontend_built() -> None:
    if not (DIST_DIR / "index.html").is_file():
        raise SystemExit("Frontend build missing. Run `npm run build` first.")


def _clean_output() -> None:
    for path in (BACKEND_DIST, BACKEND_DIST_ARM64, BACKEND_DIST_X64):
        if path.exists():
            shutil.rmtree(path)
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True, exist_ok=True)


def _pyinstaller_command(*, distpath: Path, workpath: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        str(SPEC_PATH),
        "--noconfirm",
        "--clean",
        f"--distpath={distpath}",
        f"--workpath={workpath}",
    ]


def _run_pyinstaller(*, distpath: Path, workpath: Path, darwin_arch: str | None = None) -> None:
    cmd = _pyinstaller_command(distpath=distpath, workpath=workpath)
    prefix: list[str] = []
    if darwin_arch is not None:
        prefix = ["arch", darwin_arch]

    label = darwin_arch or platform.machine()
    print(f"Building backend bundle ({label})...")
    subprocess.run([*prefix, *cmd], cwd=ROOT, check=True)


def _build_macos_universal() -> None:
    _run_pyinstaller(
        distpath=BACKEND_DIST_ARM64,
        workpath=WORK_DIR / "arm64",
        darwin_arch="arm64",
    )
    _run_pyinstaller(
        distpath=BACKEND_DIST_X64,
        workpath=WORK_DIR / "x64",
        darwin_arch="x86_64",
    )

    arm64_binary = BACKEND_DIST_ARM64 / BACKEND_NAME
    x64_binary = BACKEND_DIST_X64 / BACKEND_NAME
    BACKEND_DIST.mkdir(parents=True, exist_ok=True)
    universal_binary = BACKEND_DIST / BACKEND_NAME

    print("Creating universal backend binary with lipo...")
    subprocess.run(
        [
            "lipo",
            "-create",
            "-output",
            str(universal_binary),
            str(x64_binary),
            str(arm64_binary),
        ],
        check=True,
    )

    shutil.rmtree(BACKEND_DIST_ARM64)
    shutil.rmtree(BACKEND_DIST_X64)


def main() -> None:
    _ensure_frontend_built()
    _clean_output()

    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "PyInstaller is required. Install it with: pip install pyinstaller"
        ) from exc

    if sys.platform == "darwin":
        _build_macos_universal()
    else:
        _run_pyinstaller(distpath=BACKEND_DIST, workpath=WORK_DIR)

    print(f"Backend bundle ready in {BACKEND_DIST}")


if __name__ == "__main__":
    main()
