# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# Get ABSOLUTE path to icon
icon_path = os.path.abspath('icon.ico')

print(f"=" * 50)
print(f"Icon path: {icon_path}")
print(f"Icon exists: {os.path.exists(icon_path)}")
if os.path.exists(icon_path):
    print(f"Icon size: {os.path.getsize(icon_path)} bytes")
print(f"=" * 50)

if not os.path.exists(icon_path):
    print("ERROR: icon.ico not found!")
    icon_path = None

datas = [('calibre.zip', '.')]
if os.path.exists('icon.ico'):
    datas.append(('icon.ico', '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PIL._tkinter_finder',
        'tkinterdnd2',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='KindleSender',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_path,  # Must be absolute path
)