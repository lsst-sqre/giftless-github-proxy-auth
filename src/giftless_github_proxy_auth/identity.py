import datetime
import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional

import giftless
from giftless.auth.identity import Permission


@dataclass
class RepoAccess:
    can_write: bool
    checked_time: datetime.datetime


class Identity(giftless.auth.Identity):
    """Very basic implementation, just enough to let us know if a user
    can write to a given GitHub repo, and expire periodically."""

    def __init__(
        self,
        name: str,
        expiration: datetime.timedelta = datetime.timedelta(minutes=15),
    ) -> None:
        self.name = name
        self.id = name
        self._expiration = expiration
        self._auth: Dict[str, RepoAccess] = {}
        self._logger = logging.getLogger(__name__)
        if os.environ.get("GIFTLESS_DEBUG", ""):
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)

    def is_authorized(
        self,
        organization: str,
        repo: str,
        permission: Permission,
        oid: Optional[str],
    ) -> bool:
        # We assume all our stuff is publicly readable.  So far, that's true.
        self._logger.debug(
            f"Checking authorization for {self.name} to {organization}/{repo}"
        )
        if permission != Permission.WRITE:
            self._logger.debug(f"'{permission}' is always allowed")
            return True
        repo_str = organization + "/" + repo
        result = self.check_repo(repo_str)
        if result is None:
            # Fail closed
            return False
        return result.can_write

    def authorize_for_repo(self, repo_str: str) -> None:
        """Allow access."""
        self._logger.debug(f"Allowing access for {self.name} to {repo_str}")
        self._auth[repo_str] = RepoAccess(
            can_write=True, checked_time=datetime.datetime.now()
        )

    def deauthorize_for_repo(self, repo_str: str) -> None:
        """Deny access."""
        self._logger.debug(f"Denying access for {self.name} to {repo_str}")
        self._auth[repo_str] = RepoAccess(
            can_write=False, checked_time=datetime.datetime.now()
        )

    def check_repo(self, repo_str: str) -> Optional[RepoAccess]:
        """This lets us check for the unknown state and expiration too."""
        self._logger.debug(
            f"Checking repo access for {self.name} to {repo_str}"
        )
        state = self._auth.get(repo_str)
        if state is None:
            self._logger.debug(
                f"{self.name} auth state unknown for {repo_str}"
            )
            return None
        if datetime.datetime.now() - state.checked_time > self._expiration:
            # Data has expired.  Return None and clear the state.  We
            # need a recheck
            self._logger.debug(
                f"{self.name} auth state for {repo_str} expired: now unknown"
            )
            del self._auth[repo_str]
            return None
        self._logger.debug(f"{self.name} authorized for {repo_str}: {state}")
        return state
