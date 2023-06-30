import asyncio
import datetime
import logging
import os
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
        self._logger = logging.getLogger(__name__)
        if os.environ.get("GIFTLESS_DEBUG", ""):
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)

    def __call__(self, request: Request) -> Identity | None:
        # Get the repo name
        parts = request.path.split("/")
        org = parts[0]
        repo_name = parts[1]
        repo_path = org + "/" + repo_name
        # Extract the token
        if request.authorization is None:
            self._logger.warning(f"Unauthorized request to {repo_path}")
            return None
        token = request.authorization.password  # I think
        if token is None:
            self._logger.warning(f"No token sent for request to {repo_path}")
            return None
        auth = github.Auth.Token(token)
        # Check the cache
        identity = asyncio.run(self._cache.check(token))
        if identity is not None:
            id_state = identity.check_repo(repo_path)
            if id_state is False:
                self._logger.warning(f"Token not authorized for {repo_path}")
                return None
            if id_state is True:
                self._logger.debug(f"Token authorized for {repo_path}")
                return identity
        # The identity state for this repo is unknown
        gh = github.Github(auth=auth)
        # See whether token is valid
        self._logger.info(f"Checking validity for token for {repo_path}")
        # For now let's propagate all exceptions (and remove token from cache)
        try:
            login = gh.get_user().login
            self._logger.debug(f"Token valid and belongs to {login}")
        except Exception:
            self._logger.warning("Token not valid")
            asyncio.run(self._cache.remove(token))
            raise
        if identity is None:
            # We have a valid token for a user
            identity = Identity(name=login)
            self._logger.debug(f"Storing token for {login}")
            asyncio.run(self._cache.add(token, identity))
        # Get correct repository
        repo = gh.get_repo(repo_path)
        # See whether token gives us write access
        perms = repo.get_collaborator_permission(login)
        if perms in ("write", "admin"):
            # The answer is yes
            self._logger.debug(f"Token allows {login} write to {repo_path}")
            identity.authorize_for_repo(repo_path)
            return identity
        self.logger.warning(f"Token forbids {login} write to {repo_path}")
        identity.deauthorize_for_repo(repo_path)
        return None


def read_write(**options: Any) -> GiftlessGitHubProxyAuthenticator:
    """Allow read/write via proxy auth class."""
    return GiftlessGitHubProxyAuthenticator(**options)
