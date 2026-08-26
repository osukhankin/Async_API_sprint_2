from dataclasses import dataclass


@dataclass
class HTTPResponse:
    body: dict | list
    status: int
