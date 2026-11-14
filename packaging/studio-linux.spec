# PyInstaller spec for the Linux desktop build.
#   pip install pyinstaller
#   pyinstaller packaging/studio-linux.spec --clean
# -> dist/lookthrough-studio   (single-file executable)
# See packaging/build_linux.sh
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent  # spec lives in packaging/

hidden = (collect_submodules("engine") + collect_submodules("pipeline")
          + ["main", "batch", "webapp", "config", "desktop.launcher"])

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
    pyz, a.scripts, a.binaries, a.datas,
    name="lookthrough-studio",
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
)
