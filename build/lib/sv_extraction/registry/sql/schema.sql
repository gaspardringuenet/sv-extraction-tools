/* Level 0: echointegrations - echointegrated datasets metadata */
CREATE TABLE IF NOT EXISTS echointegrations (
    id INTEGER PRIMARY KEY,
    cruise_name TEXT NOT NULL,                                  -- Name of the cruise
    frequency_channels_kHz TEXT NOT NULL,                       -- JSON list of frequencies
    data_ping_axis_interval_type TEXT,                          -- Unit name for the ping axis (e.g., 'ping', 'nm')
    data_ping_axis_interval_value REAL,                         -- Ping axis echointegration (e.g. 3 (pings) or 1 (nm))
    data_range_axis_interval_type TEXT,                         -- Unit name for the range axis (e.g., 'meters')
    data_range_axis_interval_value REAL,                        -- Range axis echointegration (e.g., 1 (meter))
    netcdf_files TEXT NOT NULL COLLATE NOCASE,                  -- Source netCDF files (case insensitive to handle MacOS edge case)
    UNIQUE(
        cruise_name,
        frequency_channels_kHz,               
        data_ping_axis_interval_type,
        data_ping_axis_interval_value,
        data_range_axis_interval_type,
        data_range_axis_interval_value,
        netcdf_files
    )
);

/* Level 1a: images datasets (folder path and visual parameters of the printed echogram images) */
CREATE TABLE IF NOT EXISTS images_datasets (
    id INTEGER PRIMARY KEY,
    ei_id INTEGER NOT NULL,
    image_folder_path TEXT NOT NULL,                            -- Path to the folder containing the images
    time_frame_size INTEGER NOT NULL,                           -- Width of the echogram images (in ping axis indices). Last image can be smaller
    vmin REAL NOT NULL,                                         -- Minimal Sv value for color mapping
    vmax REAL NOT NULL,                                         -- Maximal Sv value for color mapping
    z_min_idx INTEGER NOT NULL,                                 -- Upper bound of the echogram images (minimal depth index)
    z_max_idx INTEGER NOT NULL,                                 -- Lower bound of the echogram images (maximal depth index)
    frequencies_kHz TEXT NOT NULL,                              -- List of frequencies used for color mapping
    colormap TEXT NOT NULL,                                     -- Colormap used ('RGB' or malplotlib colormap)
    FOREIGN KEY (ei_id) 
        REFERENCES echointegrations(id)
        ON DELETE CASCADE,
    UNIQUE(
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
);

/* Level 1b: shapes libraries (collections of LABELME shapes, drawn on any image printed out of an echointegration) */
CREATE TABLE IF NOT EXISTS shapes_libraries (
    id INTEGER PRIMARY KEY,
    ei_id INTEGER NOT NULL,                                     -- Reference echointegration
    name TEXT NOT NULL,                                         -- Name of the shapes library (user input)
    FOREIGN KEY (ei_id) 
        REFERENCES echointegrations(id)
        ON DELETE CASCADE,
    UNIQUE (name)
);

/* Level 2a: shapes (each shape is linked to a parent shapes library)*/
CREATE TABLE IF NOT EXISTS shapes (
    id TEXT PRIMARY KEY,
    library_id INTEGER NOT NULL,
    label TEXT NOT NULL,                                        -- Provided by user on shape creation in Labelme app
    shape_type TEXT NOT NULL,                                   -- Labelme shape type
    points TEXT NOT NULL,                                       -- JSON list of [x, y] points coordinates (Labelme outputs)
    bbox TEXT NOT NULL,                                         -- JSON (xmin, xmax, ymin, ymax) with xaxis = time and yaxis = depth
    geom_hash TEXT NOT NULL,                                    -- Hash to detect shape modification
    date_created TEXT NOT NULL,                                 -- Datetime of creation
    date_modified TEXT NOT NULL,                                -- Datetime of last modification
    status TEXT NOT NULL,                                       -- Status ('New', 'Modified', 'Deleted', or 'Unchanged')
    FOREIGN KEY (library_id) 
        REFERENCES shapes_libraries(id)
        ON DELETE CASCADE
);

/* Level 2b: echotypes libraries (each library is linked to a parent shapes library) */
CREATE TABLE IF NOT EXISTS echotypes_libraries (
    id INTEGER PRIMARY KEY,
    shapes_library_id INTEGER NOT NULL,                         -- Reference shapes library
    name TEXT NOT NULL,                                         -- Name of the echotypes library
    FOREIGN KEY (shapes_library_id) 
        REFERENCES shapes_libraries(id)
        ON DELETE CASCADE,
    UNIQUE (name)
);

/* Level 3: echotypes (lowest level. Each echotype is linked to a shape and an echotypes library) */
CREATE TABLE IF NOT EXISTS echotypes (
    id INTEGER PRIMARY KEY,
    library_id INTEGER NOT NULL,                                -- Id of the parent the echotypes library
    shape_id TEXT NOT NULL,                                     -- Id of the parent shape (from which the echotype was extracted)
    date_modified TEXT NOT NULL,                                -- Date of creation / modification
    clustering_features TEXT DEFAULT '{}',                      -- JSON dict (channels, delta, ref_freq)
    clustering_method TEXT DEFAULT '',                          -- Clustering models classes (supported: 'GaussianMixture', 'KMeans')
    clustering_params TEXT DEFAULT '{}',                        -- JSON dict of init params
    clustering_state BLOB DEFAULT X'',                          -- JSON of fitted params (means, covariances, ...)
    cluster_id INTEGER DEFAULT -1,                              -- Id of the selected cluster
    FOREIGN KEY (library_id) 
        REFERENCES echotypes_libraries(id)
        ON DELETE CASCADE,
    FOREIGN KEY (shape_id) 
        REFERENCES shapes(id)
        ON DELETE CASCADE
    UNIQUE (
        library_id,
        shape_id,
        clustering_features,
        clustering_method,
        clustering_params,
        clustering_state,
        cluster_id
    )
);