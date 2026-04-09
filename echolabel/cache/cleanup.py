from pathlib import Path
import logging
import shutil

from ..registry import Registry

logger = logging.getLogger(__name__)
    


def cache_cleanup(db_path: Path, cache_dir: Path) -> None:
    """Clean-up cache (db & files)
    """
    logger.info("Starting cache cleanup.")

    # Count the number of shapes within each echointegration
    with Registry(db_path, cache_dir) as registry:
        
        counts = registry.ei.count_shapes()

        logger.debug(f"Shapes counts: {counts = }")

        for row in [r for r in counts if r["count"] == 0]:
            ei_id = row["id"]

            logger.info(f"Echointegration {ei_id} contains 0 shapes. Deleting cached files and cleaning registry for this echointegration.")
            delete_images_datasets_files(registry, ei_id)

            delete_images_datasets_in_db(registry, ei_id)

    logger.info(f"End of cache cleanup. Current disk usage: {shutil.disk_usage(cache_dir)}.")



def delete_images_datasets_files(registry: Registry, ei_id: int) -> None:
    """Delete all images datasets files related to an echointegration.
    """

    logger.info("Scanning database for cache folders related to the echointegration.")

    # List images datasets
    sql = """ 
        SELECT DISTINCT(i.image_folder_path) AS path FROM echointegrations AS e
        JOIN images_datasets AS i
        ON i.ei_id = e.id
        WHERE e.id = ?;
    """
    cur = registry.conn.execute(sql, (ei_id,))
    rows = cur.fetchall()

    if not rows:
        logger.info(f"No images dataset is related to echointegration {ei_id}.")
        return
    
    rows = [dict(row) for row in rows]
    logger.info(f"Found {len(rows)} cached images folders related to echointegration {ei_id}. Proceeding to delete.")

    for row in rows:
        path = Path(row["path"])
        logger.info(f"Deleting folder {path}.")
        shutil.rmtree(path)
    
    # check if echointegration folder (parent to the images datasets folders) is now empty
    parent = path.parent
    is_empty_dir = not any(parent.iterdir())

    if is_empty_dir:
        logger.info(f"Echointegration cache folder is now empty. Folder path: {parent}")
        return
    
    logger.warning(f"Echointegration cache folder not empty. Folder path: {parent}")
    return



def delete_images_datasets_in_db(registry: Registry, ei_id: int) -> None:
    """Delete all images datasets registry entries related to an echointegration.
    """

    logger.info(f"Deleting images datasets registry entries related to echointegration {ei_id}.")

    sql = """ 
        DELETE FROM images_datasets
        WHERE ei_id = ?;
    """
    registry.conn.execute(sql, (ei_id,))
    registry.conn.commit()