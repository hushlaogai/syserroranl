# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# 项目根目录
PROJECT_DIR = os.path.abspath('.')

a = Analysis(
    ['main_entry.py'],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=[
        # 打包静态文件目录
        ('static', 'static'),
        # 打包路由模块
        ('routers', 'routers'),
        # 打包各 Python 模块
        ('app.py', '.'),
        ('database.py', '.'),
        ('models.py', '.'),
        ('schemas.py', '.'),
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.main',
        'uvicorn.config',
        'uvicorn.server',
        'uvicorn.lifespan',
        'uvicorn.lifespan.off',
        'uvicorn.lifespan.on',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'fastapi',
        'fastapi.staticfiles',
        'fastapi.responses',
        'starlette',
        'starlette.staticfiles',
        'starlette.routing',
        'starlette.middleware',
        'starlette.middleware.cors',
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.orm',
        'pydantic',
        'h11',
        'anyio',
        'anyio.abc',
        'anyio._backends._asyncio',
        'email.mime',
        'email.mime.text',
        'routers',
        'routers.systems',
        'routers.nodes',
        'routers.edges',
        'app',
        'database',
        'models',
        'schemas',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 排除不需要的大型库（来自 Anaconda）
    excludes=[
        'numpy', 'pandas', 'scipy', 'matplotlib', 'sklearn', 'cv2',
        'PIL', 'Pillow', 'IPython', 'jupyter', 'notebook',
        'tkinter', 'wx', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'tensorflow', 'torch', 'keras',
        'mkl', 'blas', 'lapack',
        'cryptography', 'nacl',
        'xmlrpc', 'ftplib', 'imaplib', 'poplib', 'smtplib',
        'setuptools', 'pip',
        'pkg_resources',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='syserroranl',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='syserroranl',
)
