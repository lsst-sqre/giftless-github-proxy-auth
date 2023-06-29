import asyncio
import datetime
from typing import Any

import giftless
import github
from flask import Request

from .cache import AuthenticationCache
from .identity import Identity


class GiftlessGitHubProxyAuthenticator(giftless.auth.Authenticator):
    """When a request is received, check to see whether that request is
    authenticated with a personal access token that would give write access
    to the repository the request is for.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._expiration = datetime.timedelta(minutes=5)
        if "expiration" in kwargs:
            self._expiration = kwargs.pop("expiration")
        super().__init__(*args, **kwargs)
        self._cache = AuthenticationCache()
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

    def __call__(self, request: Request) -> Identity | None:
        # Extract the token
        if request.authorization is None:
            return None
        token = request.authorization.password  # I think
        if token is None:
            return None
        auth = github.Auth.Token(token)
        # Get the repo name
        parts = request.path.split("/")
        org = parts[0]
        repo_name = parts[1]
        repo_path = org + "/" + repo_name
        # Check the cache
        identity = asyncio.run(self._cache.check(token))
        if identity is not None:
            id_state = identity.check_repo(repo_path)
            if id_state is False:
                return None
            if id_state is True:
                return identity
        # The identity state for this repo is unknown
        gh = github.Github(auth=auth)
        # See whether token is valid
        # For now let's propagate all exceptions (and remove token from cache)
        try:
            login = gh.get_user().login
        except Exception:
            asyncio.run(self._cache.remove(token))
            raise
        if identity is None:
            # We have a valid token for a user
            identity = Identity(name=login)
            asyncio.run(self._cache.add(token, identity))
        # Get correct repository
        repo = gh.get_repo(repo_path)
        # See whether token gives us write access
        collabs = repo.get_collaborators()
        for user in collabs:
            if user.login == login:
                # The answer is yes
                identity.authorize_for_repo(repo_path)
                return identity
        identity.deauthorize_for_repo(repo_path)
        return None
