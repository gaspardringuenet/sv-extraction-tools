from dash import dcc

def build_store():
    return [
        dcc.Store(id='selected-viz-channels', storage_type='memory'),
        dcc.Store(id='ei-metadata', storage_type='memory'),
        dcc.Store(id='selected-roi', storage_type='memory'),
        dcc.Store(id='selected-echotype', storage_type='memory'),
        dcc.Store(id='labels-da-store', storage_type='memory'),
        dcc.Store(id='viz-params', storage_type='memory'),
        dcc.Store(id='current-clustering-params', storage_type='memory'),
        dcc.Store(id='update-aggrid-flag', storage_type='memory'),
    ]