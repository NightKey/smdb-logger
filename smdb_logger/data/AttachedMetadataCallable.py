from typing import Any


class AttachedMetadataCallable:
    def __call__(self, *args, **kwargs) -> Any:
        pass
    metadata: str

