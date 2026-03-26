from dash import html, dcc

from .components.store import build_store
from .components import banner, session, table, viz, cluster, echotypebanner


def make_layout():

    return html.Div(
        className='app-grid',
        children=[

            dcc.Location(id='url'),

            # Store data in memory
            *build_store(),

            # Banner
            banner.layout(),

            # Working session info pannel
            session.layout(),

            # Overflowing data table for ROI selection / Echo-types tracking,
            table.layout(),

            # Row for ROI and echo-type viz
            viz.controls(),
            viz.graphs(),

            # Banner for echotypes main controls
            echotypebanner.layout(),

            # Row for selection and validation
            cluster.controls(),
            cluster.graphs(),
        ]
    )