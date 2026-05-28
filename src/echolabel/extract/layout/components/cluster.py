from dash import html, dcc

def controls():
    return html.Div(
        [
            html.H4("Selection params", id="select-panel-title"),
            html.Div(
                get_cluster_controls(),
                id='clustering-controls',
                className='controls'
            )
        ],
        id='select-panel',
        className='panel'
    )


def graphs():
    return html.Div(
        dcc.Tabs(
            [
                dcc.Tab(
                    label='ROI clustering result',
                    children=dcc.Graph(id='clustering-figure')
                ),
                dcc.Tab(
                    label='Selected ESUs',
                    children=dcc.Graph(id='selected-figure')
                ),
                dcc.Tab(
                    label='Left-out ESUs',
                    children=dcc.Graph(id='left-out-figure')
                ),
                dcc.Tab(
                    label='Echo-type validation',
                    children=dcc.Graph(id='validation-figure')
                ),
                dcc.Tab(
                    label='Sv-space visualization',
                    children=dcc.Graph(id='sv-dist-figure')
                )
            ],
        ),
    id='selection-tabs'
    )

def get_cluster_controls():
    return [
        html.Div([
            html.Label('Method'),
            dcc.Dropdown(
                id='clustering-method',
                options=[{'label': 'K-Means', 'value': 'KMeans'}, {'label': 'Gaussian Mixture', 'value': 'GaussianMixture'}], 
                value='KMeans',
                clearable=False
            )
        ], className='control-block'),
        html.Div([
            html.Label('Acoustic variable'),
            dcc.Dropdown(
                id='clustering-var',
                options=[{'label': 'Sv', 'value': 'Sv'}, {'label': f'ΔSv _ kHz', 'value': 'delta_Sv'}],
                value='delta_Sv',
                clearable=False
            )
        ], className='control-block'),
        html.Div([
            html.Label('Frequencies (kHz)'),
            dcc.Checklist(
                id='clustering-channels-checklist', 
                inline=True,
                persistence=True
            )
        ], className='control-block'),
        html.Div([
            html.Label('N clusters'),
            dcc.Input(
                id='clustering-n-clusters',
                type='number', 
                value=2, 
                min=1, 
                max=10, 
                step=1
            )
        ], className='control-block'),
        html.Div([
            html.Label('Selected cluster'),
            dcc.Input(
                id='cluster-id',
                type='number', 
                value=0, 
                min=0, 
                max=9, 
                step=1
            )
        ], className='control-block'),
    ]