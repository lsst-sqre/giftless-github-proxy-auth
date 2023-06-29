from giftless.auth.identity import Identity


class AuthenticationCache:
    """Class to cache authentication results, to keep us from bugging GitHub
    too often.  Encapsulated like this (and with async methods) because
    probably we're going to eventually want to use Redis or something, not
    just an in-memory data structure."""

    def __init__(self) -> None:
        self._authed: dict[str, Identity] = {}

    async def add(self, token: str, identity: Identity) -> None:
        self._authed[token] = identity

    async def remove(self, token: str) -> None:
        if token in self._authed:
            del self._authed[token]

    async def check(self, token: str) -> Identity | None:
        return self._authed.get(token)
