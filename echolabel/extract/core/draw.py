import numpy as np
import plotly.graph_objects as go
from typing import List


def scatter_shape_points(points: List[List[int]], win_xaxis_values: np.ndarray | None = None, win_yaxis_values: np.ndarray | None = None) -> go.Scatter:
    """_summary_

    Args:
        points (List[List[int]]): _description_
        win_xaxis_values (np.ndarray | None, optional): _description_. Defaults to None.
        win_yaxis_values (np.ndarray | None, optional): _description_. Defaults to None.

    Returns:
        go.Scatter: _description_
    """

    # return empty trace if no points
    if points is None:
        return go.Scatter()
    
    # format rectangle shapes 
    if len(points)==2:
        points = format_points_rectangle(points)

    # close polygons
    points = close_polygon(points)

    # get the point's coordinates and convert to time and depth
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    if win_xaxis_values is not None:
        xs = win_xaxis_values[xs]
    if win_yaxis_values is not None:
        ys = win_yaxis_values[ys]

    # add points as a trace
    return go.Scatter(
            x=xs, 
            y=ys,
            marker=dict(color='red', size=5, symbol='circle'),
            name='ROI shape',
    )


def format_points_rectangle(points: list) -> list:
    """Given a 2 points representation of a rectangle shape (diagonal edges),
    return a 4 points representation of the same shape (corners).
    """
    p = np.array(points)

    return [
        [p[:, 0].min().item(), p[:, 1].min().item()],
        [p[:, 0].min().item(), p[:, 1].max().item()],
        [p[:, 0].max().item(), p[:, 1].max().item()],
        [p[:, 0].max().item(), p[:, 1].min().item()],
    ]


def close_polygon(points: list):
    """Given a polygon represented by a list of coordinates, returns the same polygon,
    but closed (last point corresponds to first).
    """
    if points[0] != points[-1]:
        points.append(points[0])
        return points