from pathlib import Path
import traceback
from app.db import init_db
from app.store import by_workspace, create_record, get_by_id

try:
    init_db(Path('data/sales_agent.db'))
    wid = 'workspace_576d3d6923'
    rows = by_workspace('opportunities', wid)
    print('Initial rows:', len(rows))
    for o in by_workspace('opportunities', 'workspace_001'):
        cloned = dict(o)
        cloned['id'] = f"{o['id']}_{wid[-6:]}"
        cloned['workspace_id'] = wid
        create_record('opportunities', cloned, ignore_duplicate=True)
    print('After clone:', len(by_workspace('opportunities', wid)))
except Exception as e:
    traceback.print_exc()
