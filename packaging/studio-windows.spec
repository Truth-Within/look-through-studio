# PyInstaller spec for the Windows desktop build (.exe).
# Run on Windows (or a Windows CI runner):
#   pip install pyinstaller
#   pyinstaller packaging\studio-windows.spec --clean
# -> dist\LookThroughStudio.exe   (double-click -> opens the dashboard in your browser)
# See packaging/build_windows.bat and .github/workflows/release.yml
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent

hidden = (collect_submodules("engine") + collect_submodules("pipeline")
          + ["main", "batch", "webapp", "config", "desktop.launcher"])

icon = str(ROOT / "packaging" / "icon.ico")

a = Analysis(
    [str(ROOT / "desktop" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(ROOT / "web"), "web"), (str(ROOT / "README.md"), "."), (str(ROOT / "ENGINE.md"), ".")],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tests", "tkinter", "matplotlib", "numpy"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts,
    a.binaries, a.datas,
    name="LookThroughStudio",
    icon=icon if Path(icon).exists() else None,
    console=False,          # GUI app: dashboard opens in the browser
    disable_windowed_traceback=False,
    target_arch=None,
)
