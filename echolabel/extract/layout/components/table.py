from dash import dcc, html
import dash_ag_grid as dag

def layout():
    return html.Div(
        [
            get_aggrid(id='roi-data-grid'),
            html.Div(
                [
                    html.Button("Export", id='export-file-button'),
                    dcc.Download(id='export-file-download')
                ],
                id='export-controls'
            )
        ], 
        className='panel',
        id='roi-aggrid'
    )


def get_aggrid(id):

    columnDefs = [
        {
            'field': 'shape_id', 
            'headerName': 'Shape Id',
            'checkboxSelection': True,
            'headerCheckboxSelection': False,
            'width': 330
        }, 
        {'field': 'shape_label', 'headerName': 'Shape Label'},
        {'field': 'echotype_id', 'headerName': 'Echotype Id'},
        {'field': 'echotype_modified', 'headerName': 'Date Modified'},
        {'field': 'cluster_id', 'headerName': 'Cluster Id'},
        ]
    
    grid = dag.AgGrid(
        id=id,
        columnDefs=columnDefs,
        columnSize="responsiveSizeToFit",
        defaultColDef={'filter': True},
        getRowId="params.data.id",
        dashGridOptions={
            'rowSelection': 'single',
            "rowMultiSelectWithClick": False,
            'animateRows': False,
        },
        style={'height': '100%'}
    )

    return grid