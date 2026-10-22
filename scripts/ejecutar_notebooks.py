"""Ejecuta en orden con el Python activo y un kernel local al repositorio."""
from pathlib import Path
import os,sys,json,argparse
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--solo',choices=['01_preparacion_exploracion_cali.ipynb','02_primer_modelo_logistica_cali.ipynb'])
args=parser.parse_args()
for key, rel in [('JUPYTER_PATH','.jupyter'),('JUPYTER_RUNTIME_DIR','.jupyter/runtime'),
                 ('IPYTHONDIR','.jupyter/ipython'),('MPLCONFIGDIR','.cache/matplotlib'),
                 ('TEMP','.cache/tmp'),('TMP','.cache/tmp')]:
    path=ROOT/rel;path.mkdir(parents=True,exist_ok=True);os.environ[key]=str(path)
kernel=ROOT/'.jupyter/kernels/dengue-piloto';kernel.mkdir(parents=True,exist_ok=True)
(kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
    'display_name':'Python · Dengue piloto','language':'python'}),encoding='utf-8')
import nbformat
from nbclient import NotebookClient
for file in sorted((ROOT/'notebooks').glob('0[12]_*.ipynb')):
    if args.solo and file.name!=args.solo:
        continue
    nb=nbformat.read(file,as_version=4)
    print('Ejecutando',file.name,flush=True)
    client=NotebookClient(nb,timeout=300,startup_timeout=45,kernel_name='dengue-piloto',resources={'metadata':{'path':str(ROOT)}})
    client.on_cell_start=lambda cell,cell_index,**kw: print('Celda',cell_index,cell.cell_type,flush=True)
    try:
        client.execute()
    finally:
        nbformat.write(nb,file)
    print('Completado',file.name,flush=True)
