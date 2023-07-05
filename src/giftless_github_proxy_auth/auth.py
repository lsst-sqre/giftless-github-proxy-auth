import asyncio
import datetime
import logging
import os
from typing import Any, Dict, Optional, Set

import giftless
import github
from flask import Request

from .cache import AuthenticationCache
from .identity import Identity


class GiftlessGitHubProxyAuthenticator(
    giftless.auth.Authenticator, giftless.auth.PreAuthorizedActionAuthenticator
):
    """When a request is received, check to see whether that request is
    authenticated with a GitHub personal access token that would give write
    access to the repository the request is for.

    Leave room for authenticating with a Gafaelfawr token.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._expiration = datetime.timedelta(minutes=5)
        if "expiration" in kwargs:
            self._expiration = kwargs.pop("expiration")
        self._identity: Optional[Identity] = None
        if "identity" in kwargs:
            self._identity = kwargs.pop("identity")
        super().__init__(*args, **kwargs)
        self._cache = AuthenticationCache()
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._logger = logging.getLogger(__name__)
        if os.environ.get("GIFTLESS_DEBUG", ""):
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)
        self.preauth_handler = self

    def __call__(self, request: Request) -> Optional[Identity]:
        # Get the repo name
        parts = request.path.split("/")
        org = parts[1]
        repo_name = parts[2]
        repo_path = org + "/" + repo_name
        token: Optional[str] = None
        if request.authorization is None:
            if self._identity is None:
                self._logger.warning(
                    f"Request to {repo_path} has no Authorization header"
                )
                raise giftless.auth.Unauthorized("Authorization required")
            else:
                token = self._identity.token
        else:
            token = request.authorization.password
        if token is None:
            self._logger.warning(f"Request to {repo_path} has no auth token")
            raise giftless.auth.Unauthorized("Authorization token required")
        auth = github.Auth.Token(token)
        # Check the cache
        identity = asyncio.run(self._cache.check(token))
        if (
            self._identity is not None
            and identity is not None
            and identity.id != self._identity.id
        ):
            self._logger.warning(
                f"Token is for {identity.id}, not {self._identity.id}"
            )
            return None
        if identity is not None:
            # We found the token in our cache.
            id_state = identity.check_repo(repo_path)
            self._identity = identity
            if id_state is False:
                self._logger.warning(f"Token not authorized for {repo_path}")
                return None
            elif id_state is True:
                self._logger.debug(f"Token authorized for {repo_path}")
                return identity
            else:
                # id_state is None
                self._logger.debug("Token for {identity.id} not in cache")
        # Token is not in cache; see whether it is valid
        self._logger.info(f"Checking validity for token for {repo_path}")
        if token.startswith("gt-"):
            # Gafaelfawr token
            self._logger.warning("Gafaelfawr auth not yet implemented")
            return None
        # Assume it's a GitHub token (begins with "ghp_")
        # The identity state for this repo is unknown
        gh = github.Github(auth=auth)
        try:
            login = gh.get_user().login
            self._logger.debug(f"Token valid and belongs to GH:{login}")
        except Exception as exc:
            self._logger.warning(f"Token not valid for GH: {exc}")
            asyncio.run(self._cache.remove(token))
            return None
        if identity is None:
            # We have a valid token for a user
            identity = Identity(name=login, token=token)
            self._logger.debug(f"Storing token for {login}")
            asyncio.run(self._cache.add(token, identity))
            self._identity = identity
        # Get correct repository
        repo = gh.get_repo(repo_path)
        # See whether token gives us write access
        try:
            perms = repo.get_collaborator_permission(login)
        except Exception as exc:
            self._logger.warning(
                f"{login} has no permissions for GH:{repo_path}: {exc}"
            )
            return None
        if perms in ("write", "admin"):
            # The answer is yes
            self._logger.debug(f"Token allows {login} write to GH:{repo_path}")
            identity.authorize_for_repo(repo_path)
            return identity
        self.logger.warning(f"Token forbids {login} write to GH:{repo_path}")
        identity.deauthorize_for_repo(repo_path)
        return None

    def get_authz_header(
        self,
        identity: Optional[Identity] = None,
        org: str = "",
        repo: str = "",
        actions: Optional[Set[str]] = None,
        oid: Optional[str] = None,
        lifetime: Optional[int] = None,
    ) -> Dict[str, str]:
        if identity is None:
            if self._identity is None:
                self._logger.warning("No identity found for authorization")
                return {}
            identity = self._identity
        """We can use this as a pre-auth class too."""
        return {"Authorization": f"Bearer {identity.token}"}

    def get_authz_query_params(
        self,
        identity: Optional[Identity] = None,
        org: str = "",
        repo: str = "",
        actions: Optional[Set[str]] = None,
        oid: Optional[str] = None,
        lifetime: Optional[int] = None,
    ) -> Dict[str, str]:
        return self.get_authz_header(
            identity, org, repo, actions, oid, lifetime
        )


def factory(**options: Any) -> GiftlessGitHubProxyAuthenticator:
    """Allow read/write via proxy auth class."""
    return GiftlessGitHubProxyAuthenticator(**options)
