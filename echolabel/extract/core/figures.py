import numpy as np
import pandas as pd
from scipy.stats import norm
from typing import Sequence, Tuple, List, Literal
import xarray as xr

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .draw import scatter_shape_points


# ---- Default -----

def empty_figure() -> go.Figure:
    figure = go.Figure(
        data=[], 
        layout=dict(
            margin=dict(l=20, r=20, t=20, b=20),
        )
    )
    return figure


# ---- Echograms ----

def make_roi_fig(
    sv: xr.DataArray, 
    cmap: str, 
    frequencies: Sequence[float], 
    sv_range: Tuple[float, float],
    shape_type: str = None,
    points: list = None
) -> go.Figure:
    """Return an echogram of the acoustic data contained in sv as a go.Figure. Trace the ROI's shape using the shape's points (Labelme format).

    Args:
        sv (xr.DataArray): Acoustic Sv data.
        cmap (str): Colormap (either 'RGB' to map 3 frequencies or a px.colors.named_colorscales()).
        frequencies (Sequence[float]): Frequencies to map (either one or 3).
        sv_range (Tuple[float, float]): Range of Sv values (in dB) for color mapping.
        shape_type (str, optional): Labelme shape type. Defaults to None.
        points (list, optional): Labelme shape points as a list of [x, y] coordinates. Defaults to None.

    Raises:
        ValueError: If the number of frequencies does not correspond to the colormap.

    Returns:
        go.Figure: Echogram figure.
    """

    sv = sv.sel(channel=frequencies)

    # 3-channel RGB echogram
    if cmap == 'RGB' and len(frequencies) == 3:
        fig = fig_rgb(sv, vmin=sv_range[0], vmax=sv_range[1])
        
        # Add ROI shape
        if points and shape_type:
            fig.add_trace(scatter_shape_points(points))

    # Single channel plot
    elif len(frequencies) == 1:
        fig = fig_single_channel(sv, cmap, vmin=sv_range[0], vmax=sv_range[1])

        # Add ROI shape
        if points and shape_type:
            fig.add_trace(scatter_shape_points(points, sv.time.values, sv.depth.values))

    # Mismatch between frequencies and cmap
    else:
        raise ValueError(f"Number of frequencies ({len(frequencies)}) different from 1 in single channel plot.")
    
    # Reduce margins
    fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))

    return fig


def fig_rgb(sv: xr.DataArray, vmin: float, vmax: float) -> go.Figure:

    data = sv.values
    img = (data - vmin) / (vmax - vmin)
    img = np.clip(img, 0, 1)
    img = np.nan_to_num(img, nan=0)

    fig = px.imshow(
        img,
        zmin=0,
        zmax=1,
        labels=dict(x='ESU', y='Depth samples')
    )

    fig.add_trace(go.Heatmap(
        name="",
        z=data[:, :, 0],
        customdata=data,
        opacity=0.,
        showscale=False,
        hovertemplate="R: %{customdata[0]:.1f}<br>G: %{customdata[1]:.1f}<br>B: %{customdata[2]:.1f}"
    ))

    return fig
            

def fig_single_channel(sv: xr.DataArray, cmap: str, vmin: float, vmax: float) -> go.Figure:

    fig = px.imshow(
        sv.squeeze(), 
        color_continuous_scale=cmap, 
        zmin=vmin, 
        zmax=vmax,
        labels=dict(color=f"{sv.name} [{sv.attrs.get('units')}]")
    )

    return fig


# ---- Validation plots ----

def make_validation_plots(sv: xr.DataArray, frequencies: List[float | int], ref_frequency: float | int) -> go.Figure:

    if ref_frequency is None:
        return empty_figure()

    # Plotly default color cycle
    PLOTLY_COLORS = px.colors.qualitative.Plotly

    # Sort frequency channels
    frequencies = frequencies.copy()
    frequencies.sort()

    # Precompute DataFrame's and aggregations
    _, sv_agg = compute_aggs(sv, frequencies, ref_frequency, var="sv")
    delta_sv_df, delta_sv_agg = compute_aggs(sv, frequencies, ref_frequency, var="delta_sv")

    # Create fig with subplots
    fig = make_subplots(
        rows=2,
        cols=2,
        specs= [[{"colspan": 2}, None],
                [{}, {}]]
    )

    # Build Histogram traces and track their indices
    hist_traces = []
    x_gauss = np.linspace(-50, 50, 300)

    non_ref = delta_sv_df[delta_sv_df["channel"] != ref_frequency]

    # Histograms of delta Sv (exclude ref frequency)
    for i, (c, sub) in enumerate(non_ref.groupby('channel')):
        color = PLOTLY_COLORS[i % len(PLOTLY_COLORS)]

        # Histogram
        fig.add_trace(
            go.Histogram(
                x=sub["delta_sv"],
                xbins=dict(start=-50., end=50., size=0.5),
                histnorm="probability density",
                opacity=0.3,
                name=f"{int(c)}-{int(ref_frequency)} kHz",
                marker_color=color
            ),
            row=1, col=1
        )

        # Fit Gaussian and scale to match probability histogram (bin width = 0.5)
        mu, sigma = norm.fit(sub["delta_sv"].dropna())
        with np.errstate(divide="ignore"):
            y_gauss = norm.pdf(x_gauss, mu, sigma)
        fig.add_trace(
            go.Scatter(
                x=x_gauss,
                y=y_gauss,
                mode="lines",
                name=f"Gaussian {int(c)}-{int(ref_frequency)} kHz (μ={mu:.1f}, σ={sigma:.1f})",
                line=dict(width=2),
                showlegend=True,
                marker_color=color
            ),
            row=1, col=1
        )

        hist_traces.append(c)

    # Relative frequency response curve
    fig.add_traces(
        data=mean_and_sd_lineplot(
            delta_sv_agg, 
            line_name=f"Rel. frequency response\n(ref. {ref_frequency} kHz)"
        ),
        rows=[2, 2, 2],
        cols=[1, 1, 1]
    )

    # Absolute frequency response curve
    fig.add_traces(
        data=mean_and_sd_lineplot(
            sv_agg, 
            line_name=f"Abs. frequency response",
            line_color="blue"
        ),
        rows=[2, 2, 2],
        cols=[2, 2, 2]
    )

    # Buttons
    # [hist_0, gauss_0, hist_1, gauss_1, ...] then line plot traces
    n_freq = len(hist_traces)
    n_hist_gauss = n_freq * 2       # pairs: (histogram, gaussian) per frequency
    n_total = len(fig.data)
    n_lines = n_total - n_hist_gauss

    def make_visibility(selected_idx=None, show_gaussians=True):
        """Build visibility list. selected_idx=None means show all histograms."""
        vis = []
        for i in range(n_freq):
            is_selected = selected_idx is None or i == selected_idx
            vis.append(is_selected)            # histogram
            vis.append(is_selected and show_gaussians)  # gaussian
        vis += [True] * n_lines                # always show line plots
        return vis

    # Dropdown: filter by frequency
    freq_buttons = [
        {"label": "All", "method": "restyle", "args": [{"visible": make_visibility()}]}
    ] + [
        {
            "label": f"{int(c)}-{int(ref_frequency)} kHz",
            "method": "restyle",
            "args": [{"visible": make_visibility(selected_idx=idx)}]
        }
        for idx, c in enumerate(hist_traces)
    ]

    # Single toggle button for Gaussians
    gauss_buttons = [
        {
            "label": "Gaussians",
            "method": "restyle",
            "args":  [{"visible": make_visibility(show_gaussians=True)}],   # when toggled ON
            "args2": [{"visible": make_visibility(show_gaussians=False)}],  # when toggled OFF
        }
    ]

    fig.update_layout(
        updatemenus=[
            dict(
                type="dropdown",
                direction="down",
                x=0.0, xanchor="left",
                y=1.15, yanchor="top",
                buttons=freq_buttons,
                showactive=True,
            ),
            dict(
                type="buttons",
                direction="right",
                x=0.2, xanchor="left",
                y=1.15, yanchor="top",
                buttons=gauss_buttons,
                showactive=True,  # highlights the button when active
            ),
        ]
    )

    # Layout
    fmin, fmax = frequencies[0], frequencies[-1]

    fig.update_layout(
        barmode='overlay',
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis1=dict(title='ΔSv [dB]',
                    range=[-30., 30.]),
        yaxis1=dict(title='Probability density'),
        xaxis2=dict(title='Sampling frequency [kHz]',
                    range=[fmin-10, fmax+10],
                    tickvals=frequencies),
        yaxis2=dict(title='ΔSv [dB]',
                    range=[-20, 20]),
        xaxis3=dict(title='Sampling frequency [kHz]',
                    range=[fmin-10, fmax+10],
                    tickvals=frequencies),
        yaxis3=dict(title='Sv [dB]',
                    range=[-90, -50]),
        )
    
    return fig


def compute_aggs(sv, frequencies, ref_frequency, var: Literal["sv", "delta_sv"]) -> Tuple[pd.DataFrame, pd.DataFrame]:

    if var == "delta_sv":
        da = sv.sel(channel=frequencies) - sv.sel(channel=ref_frequency)
    else:
        da = sv
    
    df = (
        da
        .sel(channel=frequencies)
        .stack(pixel=("time", "depth"))
        .dropna(dim="pixel", how="any")
        .to_dataframe(name=var)
        .reset_index()
    )

    # Compute aggregations
    agg = (
        df
        .groupby("channel")[var]
        .agg(mean = "mean", sd = "std")
        .reset_index()
    )

    return df, agg

def mean_and_sd_lineplot(df: pd.DataFrame, line_name: str, line_color="red") -> List[go.Scatter]:

    data = [
        go.Scatter(
            name=line_name,
            x=df["channel"],
            y=df["mean"],
            marker=dict(color=line_color)
        ),
        go.Scatter(
            name="Upper Bound",
            x=df["channel"],
            y=df["mean"]+df["sd"],
            mode="lines",
            line=dict(width=0),
            showlegend=False
        ),
        go.Scatter(
            name="Lower Bound",
            x=df["channel"],
            y=df["mean"]-df["sd"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor='rgba(68, 68, 68, 0.3)',
            showlegend=False
        )
    ]

    return data
