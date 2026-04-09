"""SQL statements for echotypes table"""

GET_CHILDREN_ECHOTYPES_LIBS = """
    SELECT DISTINCT children.name FROM
    echotypes_libraries AS children
    JOIN shapes_libraries AS parents
    ON children.shapes_library_id = parents.id
    WHERE parents.name = ?;
"""

GET_SHAPES_LIB_ID = "SELECT id FROM shapes_libraries WHERE name = ?;"

INSERT_ECHOTYPES_LIB = """
    INSERT INTO echotypes_libraries (
        shapes_library_id,
        name
    )
    VALUES (?, ?)
    ON CONFLICT DO NOTHING
    RETURNING id;
"""

DELETE_ECHOTYPES_LIB = """
    DELETE FROM echotypes_libraries
    WHERE name = ?;
"""

LIST_IDS_IN_LIB = """
    SELECT 
        e.id AS echotype_id,
        e.shape_id AS shape_id
    FROM echotypes AS e
    JOIN echotypes_libraries AS el
    ON e.library_id = el.id
    WHERE el.name = ?;
"""

MAKE_AGGRID = """
    WITH target_library AS (
        -- Get the library ID from its unique name
        SELECT id, shapes_library_id
        FROM echotypes_libraries
        WHERE name = ?
    ),
    parent_shapes AS (
        -- All shapes in the parent shapes library of this echotypes library
        SELECT s.*
        FROM shapes s
        JOIN shapes_libraries sl ON s.library_id = sl.id
        JOIN target_library tl ON sl.id = tl.shapes_library_id
        WHERE s.shape_type IN ('rectangle', 'polygon', 'cirlce')
    )
    SELECT
        s.id AS shape_id,
        s.label AS shape_label,
        e.id AS echotype_id,
        e.date_modified AS echotype_modified,
        e.cluster_id AS cluster_id
    FROM parent_shapes s
    LEFT JOIN echotypes e
        ON e.shape_id = s.id
        AND e.library_id = (SELECT id FROM target_library)
    ORDER BY s.id, e.id;
"""

SELECT_WITH_ID = "SELECT * FROM echotypes WHERE id = ?"

GET_ECHOTYPES_LIB_ID = "SELECT id FROM echotypes_libraries WHERE name = ?;"

INSERT_ECHOTYPE = """
    INSERT INTO echotypes (
        library_id,
        shape_id,
        date_modified,
        clustering_features,
        clustering_method,
        clustering_params,
        clustering_state,
        cluster_id
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT DO NOTHING
    RETURNING id;
"""

UPDATE_ECHOTYPE = """
    UPDATE echotypes
    SET date_modified = ?,
        clustering_features = ?,
        clustering_method = ?,
        clustering_params = ?,
        clustering_state = ?,
        cluster_id = ?
    WHERE id = ?;
"""

DELETE_ECHOTYPE = """
    DELETE FROM echotypes
    WHERE id = ?;
"""

COPY_ECHOTYPES_LIB = """
    INSERT INTO echotypes_libraries (shapes_library_id, name)
    SELECT shapes_library_id, ?
    FROM echotypes_libraries
    WHERE id = ?
    ON CONFLIC DO NOTHING
    RETURNING id;
"""

COPY_ECHOTYPES_ENTRIES = """
    INSERT INTO echotypes (
        library_id,
        shape_id,
        date_modified,
        clustering_features,
        clustering_method,
        clustering_params,
        clustering_state,
        cluster_id
    )
    SELECT ?, shape_id, date_modified, clustering_features, clustering_method, clustering_params, clustering_state, cluster_id
    FROM echotypes
    WHERE library_id = ?
"""