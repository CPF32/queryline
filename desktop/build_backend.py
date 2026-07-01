"""Build the bundled Python backend used by packaged desktop installers."""

from __future__ import annotations

import os
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
X86_VENV_PYTHON = ROOT / ".venv-x86" / "bin" / "python"


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


def _python_machine(python_executable: str) -> str:
    result = subprocess.run(
        [python_executable, "-c", "import platform; print(platform.machine())"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().lower()


def _resolve_x86_python() -> str:
    configured = os.environ.get("QUERYLINE_X86_PYTHON", "").strip()
    if configured:
        return configured
    if X86_VENV_PYTHON.is_file():
        return str(X86_VENV_PYTHON)
    raise SystemExit(
        "x86_64 backend build requires an x86_64 Python with its own dependencies.\n"
        "Set QUERYLINE_X86_PYTHON or create .venv-x86:\n"
        "  arch -x86_64 $(which python3) -m venv .venv-x86\n"
        "  arch -x86_64 .venv-x86/bin/pip install -r requirements.txt"
    )


def _python_for_darwin_arch(target_arch: str) -> tuple[str, list[str]]:
    if target_arch == "arm64":
        python_executable = sys.executable
        expected = {"arm64", "aarch64"}
    elif target_arch == "x86_64":
        python_executable = _resolve_x86_python()
        expected = {"x86_64", "amd64"}
    else:
        raise ValueError(f"Unsupported macOS arch: {target_arch}")

    actual = _python_machine(python_executable)
    if actual not in expected:
        raise SystemExit(
            f"Expected {target_arch} Python for backend build, got {actual!r} "
            f"from {python_executable}"
        )

    return python_executable, []


def _pyinstaller_command(
    *,
    distpath: Path,
    workpath: Path,
    python_executable: str,
) -> list[str]:
    return [
        python_executable,
        "-m",
        "PyInstaller",
        str(SPEC_PATH),
        "--noconfirm",
        "--clean",
        f"--distpath={distpath}",
        f"--workpath={workpath}",
    ]


def _run_pyinstaller(*, distpath: Path, workpath: Path, darwin_arch: str | None = None) -> None:
    if darwin_arch is not None:
        python_executable, prefix = _python_for_darwin_arch(darwin_arch)
    else:
        python_executable, prefix = sys.executable, []

    cmd = _pyinstaller_command(
        distpath=distpath,
        workpath=workpath,
        python_executable=python_executable,
    )

    label = darwin_arch or platform.machine()
    print(f"Building backend bundle ({label}) with {python_executable}...")
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
    subprocess.run(["lipo", "-info", str(universal_binary)], check=True)

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
