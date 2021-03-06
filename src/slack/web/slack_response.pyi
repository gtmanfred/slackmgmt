from typing import Any, Optional

class SlackResponse:
    http_verb: Any = ...
    api_url: Any = ...
    req_args: Any = ...
    data: Any = ...
    headers: Any = ...
    status_code: Any = ...
    def __init__(self, client: Any, http_verb: str, api_url: str, req_args: dict, data: dict, headers: dict, status_code: int) -> None: ...
    def __getitem__(self, key: Any): ...
    def __iter__(self) -> Any: ...
    def __next__(self): ...
    def get(self, key: Any, default: Optional[Any] = ...): ...
    def validate(self): ...
