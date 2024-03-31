# -*- mode: python ; coding: utf-8 -*-

"""
Copyright (c) 2024 Fern Lane

This file is part of LlM-Api-Open (LMAO) project.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import platform

import PyInstaller.config

# Set working path
PyInstaller.config.CONF["workpath"] = "./build"

# Source files INSIDE src/lmao
SOURCE_FILES = [
    "main.py",
    "module_wrapper.py",
    "external_api.py",
    "proxy_extension.py",
    "_version.py",
    os.path.join("chatgpt", "chatgpt_api.py"),
    os.path.join("ms_copilot", "ms_copilot_api.py"),
]
_sources = [os.path.join("src", "lmao", source_file) for source_file in SOURCE_FILES]

# Final name
COMPILE_NAME = f"lmao-{platform.system()}-{platform.machine()}".lower()

# Files and folders to include inside builded binary
INCLUDE_FILES = [
    (os.path.join("configs", "*.json"), "."),
    (os.path.join("src", "lmao", "chatgpt", "*.js"), os.path.join("lmao", "chatgpt")),
    (os.path.join("src", "lmao", "ms_copilot", "*.js"), os.path.join("lmao", "ms_copilot")),
]

block_cipher = None

a = Analysis(
    _sources,
    pathex=[],
    binaries=[],
    datas=INCLUDE_FILES,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["_bootlocale"],
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
    a.datas,
    [],
    name=COMPILE_NAME,
    debug=False,
    bootloader_ignore_signals=True,
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
    icon=[os.path.join("brandbook", "icon.ico")],
)
