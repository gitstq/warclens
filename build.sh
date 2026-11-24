#!/usr/bin/env bash
# WarcLens 一键打包脚本
# 生成源码分发包 (sdist) 与轮文件 (wheel)，两者均为纯 Python、零依赖。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "==> [1/4] 环境检查"
python3 --version

echo "==> [2/4] 运行全量单元测试"
python3 -m unittest discover -s tests
echo "    ✓ 全部测试通过"

echo "==> [3/4] 构建分发包 (sdist + wheel)"
rm -rf dist build *.egg-info
if python3 -m build --version >/dev/null 2>&1; then
    python3 -m build --sdist --wheel
else
    echo "    ! 未安装 build 模块，回退到 setup.py 构建"
    python3 setup.py sdist bdist_wheel 2>/dev/null || {
        echo "    ✗ 构建依赖缺失：请 pip install build wheel" >&2
        exit 1
    }
fi

echo "==> [4/4] 校验产物"
ls -lh dist/
python3 - <<'PY'
import glob, zipfile, tarfile
wheels = glob.glob("dist/*.whl")
sdists = glob.glob("dist/*.tar.gz")
assert wheels, "未生成 wheel"
assert sdists, "未生成 sdist"
with zipfile.ZipFile(wheels[0]) as z:
    names = z.namelist()
    assert "warclens/__init__.py" in names, "wheel 缺少核心模块"
    assert any(n.endswith("entry_points.txt") for n in names), "wheel 缺少 CLI 入口"
with tarfile.open(sdists[0]) as t:
    assert any(n.endswith("README.md") for n in t.getnames()), "sdist 缺少 README"
print("    ✓ wheel 与 sdist 结构校验通过")
PY

echo "==> 打包完成，产物位于 dist/"
