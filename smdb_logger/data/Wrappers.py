from typing import Callable, cast

from smdb_logger.data import AttachedMetadataCallable


def attach_metadata(metadata: str):
    def decorator(func: Callable):
        func.metadata = metadata
        return cast(AttachedMetadataCallable, func)

    return decorator