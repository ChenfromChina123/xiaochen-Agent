# -*- mode: python ; coding: utf-8 -*-
"""
小晨终端助手 Linux 构建配置
使用此 spec 文件可以确保所有模块和数据文件正确打包
"""
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

# 获取项目根目录（spec 文件在 xiaochen_agent_v2/packaging/，所以根目录是 ../..）
block_cipher = None
project_root = os.path.abspath(os.path.join(SPECPATH, '../..'))
xiaochen_path = os.path.join(project_root, 'xiaochen_agent_v2')

# 收集所有子模块
hiddenimports = [
    'xiaochen_agent_v2',
    'xiaochen_agent_v2.core',
    'xiaochen_agent_v2.core.agent',
    'xiaochen_agent_v2.core.config',
    'xiaochen_agent_v2.core.config_manager',
    'xiaochen_agent_v2.core.metrics',
    'xiaochen_agent_v2.core.session',
    'xiaochen_agent_v2.core.task_manager',
    'xiaochen_agent_v2.core.utils',
    'xiaochen_agent_v2.ui',
    'xiaochen_agent_v2.ui.cli',
    'xiaochen_agent_v2.tools',
    'xiaochen_agent_v2.tools.executor',
    'xiaochen_agent_v2.tools.image',
    'xiaochen_agent_v2.tools.ocr',
    'xiaochen_agent_v2.tools.web_search',
    'xiaochen_agent_v2.utils',
    'xiaochen_agent_v2.utils.console',
    'xiaochen_agent_v2.utils.display',
    'xiaochen_agent_v2.utils.files',
    'xiaochen_agent_v2.utils.interrupt',
    'xiaochen_agent_v2.utils.logs',
    'xiaochen_agent_v2.utils.process_tracker',
    'xiaochen_agent_v2.utils.tags',
    'xiaochen_agent_v2.utils.terminal',
]

# 数据文件
datas = []

# 添加静态文件
static_path = os.path.join(xiaochen_path, 'static')
if os.path.exists(static_path):
    datas.append((static_path, 'xiaochen_agent_v2/static'))

# 添加配置文件
config_files = ['config.json', 'ocr_config.json']
for config_file in config_files:
    config_path = os.path.join(xiaochen_path, config_file)
    if os.path.exists(config_path):
        datas.append((config_path, 'xiaochen_agent_v2'))

a = Analysis(
    [os.path.join(xiaochen_path, 'packaging', 'launcher.py')],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='xiaochen-agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

