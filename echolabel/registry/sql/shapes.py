"""SQL statements for shapes_libraries and shapes table"""

# Shapes libraries registry management

INSERT_SHAPES_LIB = """
    INSERT INTO shapes_libraries (
        ei_id,
        name
    )
    VALUES (?, ?)
    ON CONFLICT DO NOTHING
    RETURNING id 
"""

GET_SHAPES_LIB_ID_FROM_VALUES = """
    SELECT id FROM shapes_libraries
    WHERE ei_id = ?
        AND name = ?
"""

# Shapes registry management

INSERT_SHAPE = """
    INSERT INTO shapes (
        id,
        library_id,
        label,
        shape_type,
        points,
        bbox,
        geom_hash,
        date_created,
        date_modified,
        status
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

UPDATE_SHAPE = """
    UPDATE shapes
    SET label = ?,
        shape_type = ?, 
        points = ?,
        bbox = ?,
        geom_hash = ?, 
        date_modified = ?, 
        status = ?
    WHERE id = ?
"""

SET_STATUS = "UPDATE shapes SET status = ? WHERE id = ?"

REMOVE_DELETED = "DELETE FROM shapes WHERE status = 'deleted'"

SELECT_WITH_ID = "SELECT * FROM shapes WHERE id = ?"

# Interact with both tables

def set_deleted(shape_ids: list | None = None) -> str:
    """Formats a query to set the status of certain shapes (not contained in shape_id + belonging to a given library)
    to deleted.
    """

    # No shape_ids -> delete all shapes in library
    if not shape_ids: 
        return """
            UPDATE shapes
            SET status = 'deleted'
            WHERE library_id = (
                SELECT id FROM shapes_libraries
                WHERE name = ?
            )
        """
    
    # Delete all shapes in library, except those in shape_ids
    placeholders = ",".join("?" for _ in shape_ids)
    return f"""
        UPDATE shapes
        SET status = 'deleted'
        WHERE library_id = (
            SELECT id FROM shapes_libraries
            WHERE name = ?
        )
        AND id NOT IN ({placeholders})
    """

REMOVE_EMPTY_SHAPES_LIB = """
    DELETE FROM shapes_libraries
    WHERE id NOT IN (
        SELECT library_id FROM shapes
    )
"""

SELECT_VALID_SHAPES_IN_LIB = """
    SELECT id FROM shapes
    JOIN shapes_libraries AS lib
    ON shapes.library_id = lib.id
    WHERE shapes.status != 'deleted' AND lib.name = ?
"""

COUNT_LIB_SHAPES_BY_STATUS = """
    SELECT COUNT(*) FROM shapes 
    JOIN shapes_libraries AS lib
    ON shapes.library_id = lib.id
    WHERE shapes.status = ? AND lib.name = ?
"""