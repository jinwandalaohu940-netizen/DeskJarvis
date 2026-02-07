# === DeskJarvis dry-run guard ===
import os as _dj_os
import shutil as _dj_shutil
import subprocess as _dj_subprocess
from pathlib import Path as _dj_Path

def _dj_block(*args, **kwargs):
    raise RuntimeError('DESKJARVIS_BLOCKED_OPERATION: blocked in dry-run')

# 阻断删除/移动等高风险操作
_dj_os.remove = _dj_block
_dj_os.unlink = _dj_block
_dj_shutil.rmtree = _dj_block
_dj_shutil.move = _dj_block
_dj_shutil.copytree = _dj_block
_dj_subprocess.run = _dj_block
_dj_subprocess.Popen = _dj_block

# Path 级别删除也阻断
_dj_Path.unlink = _dj_block
_dj_Path.rmdir = _dj_block


print(1+1)