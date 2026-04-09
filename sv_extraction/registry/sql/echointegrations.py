INSERT_EI = """
    INSERT INTO echointegrations (
        cruise_name,
        frequency_channels_kHz, 
        data_ping_axis_interval_type,
        data_ping_axis_interval_value,
        data_range_axis_interval_type,
        data_range_axis_interval_value,
        netcdf_files
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT DO NOTHING
    RETURNING id;                       -- this line requires SQLite >= 3.35
"""

GET_ID_FROM_VALUES = """
    SELECT id FROM echointegrations
    WHERE cruise_name = ?
        AND frequency_channels_kHz = ?
        AND data_ping_axis_interval_type = ?
        AND data_ping_axis_interval_value = ?
        AND data_range_axis_interval_type = ?
        AND data_range_axis_interval_value = ?
        AND netcdf_files = ?;
"""

DELETE_EI = """
    DELETE FROM echointegrations
    WHERE id = ?;
"""

COUNT_SHAPES = """
    SELECT e.id AS id, count(s.id) AS count FROM echointegrations AS e
    LEFT JOIN shapes_libraries AS slib ON slib.ei_id = e.id
    LEFT JOIN shapes AS s ON s.library_id = slib.id
    GROUP BY e.id;
"""