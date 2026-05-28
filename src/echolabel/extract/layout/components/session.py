from dash import html, dcc

def layout():
    return html.Div(
        [
            html.H4("Session controls"), 
            html.Div(
                [html.Div(control, style={"flex": "1", "margin": "0 2px"}) for control in session_controls()],
                style={"display": "flex", "flex-direction": "row"}
            ),
            session_info(),
            html.Div(
                echotype_library_controls(),
            )
        ],
        className='panel',
        id='session-control',
    )


def session_controls():
    return [
        html.Div([
            html.Label('ROI library'),
            dcc.Dropdown(
                id='roi-library',
                options=[],
                value=None,
                clearable=False,
                persistence=True,
            )
        ], className='control-block'),
    ]


def session_info():

    text = f"""
        **Echointegration infos:**
        -   Cruise name: `_` 
        -   Pings axis: `_`
        -   Range axis: `_`
        -   Registry id: `_`
    """

    return dcc.Markdown(
        id='session-info-text',
        children=text
    )



def echotype_library_controls():

    return [

        html.Div(
            [
                html.Div([
                    html.Label('Select echo-type library from name:'),
                    dcc.Dropdown(id='select-echotype-lib', persistence=True),
                    html.Button('Delete', id='echotype-library-delete')
                ], 
                className='control-block',
                id='library-selection-block',
                style={"flex": "1", "margin": "0 2px"}
                ),

                html.Div(
                    [
                        html.Button('Create new library', id='echotype-library-create-new'),
                        html.Div([
                            html.Label('Input new echo-type library name:'),
                            html.Div([
                                dcc.Input(
                                    id='echotype-library-input', 
                                    placeholder='Input new name...', 
                                    type='text', 
                                    disabled=True,
                                    pattern=r"[A-Za-z0-9][A-Za-z0-9_-]*",
                                    debounce=True,
                                ),
                                html.Button('Add', id='echotype-library-add', disabled=True),
                                html.Button('Exit', id='echotype-library-exit', disabled=True)
                            ], id='library-creation-controls'),
                        ], 
                        className='control-block',
                        id='library-creation-block',
                        ),
                    ],
                    className='control-block',
                    style={'color':'#ccc', "flex": "1", "margin": "0 2px"}
                ),
            ],
            style={"display": "flex", "flex-direction": "row"}
        ),
    ]