from dash import html, dcc

def controls():
    return html.Div(
        [
            html.Div(html.H4("Visualization parameters"), id='viz-panel-title'),
            html.Div(
                get_roi_viz_controls(),
                className='controls',
                id='viz-controls'
            ),
            html.Div(
                get_db_slider(),
                id='slider',
                className='controls'
            ),
        ],
        className="panel",
        id="viz-panel"
    )

def graphs():
    return html.Div(
        dcc.Tabs(
            [
                dcc.Tab(
                    label='ROI',
                    children= dcc.Graph(id='roi-figure')
                ),
                dcc.Tab(
                    label='Echo-type',
                    children=dcc.Graph(id='echotype-figure')
                )
            ],
        ),
        id='roi-n-echotype-figs'
    )


def get_roi_viz_controls():

    return [
        html.Div([
            html.Label('Mode'),
            dcc.Dropdown(
                id='roi-viz-mode',
                options=['RGB', 'Single channel'], 
                searchable=False,
                clearable=False
            )
        ], className='control-block'),
        html.Div([
            html.Label('Frequencies (kHz)'),
            dcc.Checklist(
                id='roi-viz-frequencies', 
                inline=True
            )
        ], className='control-block'),
        html.Div([
            html.Label('Colormap'),
            dcc.Dropdown(
                id='roi-viz-cmap',
                clearable=False
            )
        ], className='control-block'),
        html.Fieldset(
            [
                html.Legend("Window"),

                html.Div([
                    html.Label("Minimal width (ESU)"),
                    dcc.Input(
                        id='roi-viz-min-width',
                        type='number',
                        value=100,
                        min=100,
                        max=10_000,
                        step=1
                    ),
                ], className="sub-control"),

                html.Div([
                    html.Label("Minimal height (Depth samples)"),
                    dcc.Input(
                        id='roi-viz-min-height',
                        type='number',
                        value=30,
                        min=30,
                        max=1000,
                        step=1,
                    ),
                ], className="sub-control"),
            ],
            className="control-block"
        )

    ]


def get_db_slider():
    return [
        html.B("Sv range [dB]"),
        dcc.RangeSlider(
            id='roi-viz-db-slider',
            min=-150, max=0, step=1, 
            marks={i:str(i) for i in range(-150, 0, 10)},
            count=1,
            value=[-90, -50],
            vertical = True,
            tooltip={"placement": "bottom", "always_visible": True, "template": "{value} dB"}
        ),
    ]
