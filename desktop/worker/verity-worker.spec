# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from pathlib import Path
datas,binaries,hiddenimports=collect_all('insightface')
if Path('models').exists(): datas.append(('models','models'))
a=Analysis(['worker_entry.py'],pathex=['.'],binaries=binaries,datas=datas,hiddenimports=hiddenimports+['uvicorn.logging','uvicorn.loops.auto','uvicorn.protocols.http.auto','uvicorn.protocols.websockets.auto'],noarchive=False)
pyz=PYZ(a.pure); exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='verity-worker',console=False)
