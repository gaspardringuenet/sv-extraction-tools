EI_FROM_SHAPES_LIB = """
    SELECT DISTINCT
        ei.id
    FROM echointegrations AS ei
    JOIN shapes_libraries AS lib
    ON lib.ei_id = ei.id
    WHERE lib.name = ?;
"""