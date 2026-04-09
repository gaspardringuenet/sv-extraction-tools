
from dash import html, dcc


RADIO_ITEMS_OPTS = [
    {
        "label": [
            html.Img(src="../../assets/images/search.svg", height=20, style={"padding-left": 10}),
            html.Span("Inspect", style={"font-size": 15, "padding-left": 10, "padding-right": 20})
        ],
        "value": "inspect"
    },
        {
        "label": [
            html.Img(src="../../assets/images/pencil-square.svg", height=20, style={"padding-left": 10}),
            html.Span("Edit", style={"font-size": 15, "padding": 10, "padding-right": 20})
        ],
        "value": "edit"
    },
    {
        "label": [
            html.Img(src="../../assets/images/plus-square.svg", height=20, style={"padding-left": 10}),
            html.Span("New", style={"font-size": 15, "padding-left": 10})
        ],
        "value": "new"
    },
]


def layout():
    return html.Div([
        html.H4("Echotype extraction"),
        html.Div([
            dcc.RadioItems(value='inspect', options=RADIO_ITEMS_OPTS, id='echotype-mode', inline=True),            
        ]),
        html.Div([
            html.Button('Save echotype', id='echotype-save-button'),
            html.Button('Delete echotype', id='echotype-delete-button'),
        ])
    ],
    id='echotype-banner',
    className='banner'
    )