GET_ID_FROM_VALUES = """
    SELECT id FROM images_datasets
    WHERE ei_id = ?
        AND image_folder_path = ?
        AND time_frame_size = ?
        AND vmin = ?
        AND vmax = ?
        AND z_min_idx = ?
        AND z_max_idx = ?
        AND frequencies_kHz = ?
        AND colormap = ?
"""

INSERT = """
    INSERT INTO images_datasets (
        ei_id,
        image_folder_path,
        time_frame_size,
        vmin,
        vmax,
        z_min_idx,
        z_max_idx,
        frequencies_kHz,
        colormap
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT DO NOTHING
    RETURNING id;
"""