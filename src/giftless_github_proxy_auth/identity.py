import datetime
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
        token: str,
        expiration: datetime.timedelta = datetime.timedelta(minutes=15),
    ) -> None:
        self.name = name
        self.token = token
        self._expiration = expiration
        self._auth: Dict[str, RepoAccess] = {}

    def is_authorized(
        self,
        organization: str,
        repo: str,
        permission: Permission,
        oid: Optional[str],
    ) -> bool:
        # We assume all our stuff is publicly readable.  So far, that's true.
        if permission != Permission.WRITE:
            return True
        repo_str = organization + "/" + repo
        result = self.check_repo(repo_str)
        if result is None:
            # Fail closed
            return False
        return result.can_write

    def authorize_for_repo(self, repo_str: str) -> None:
        """Allow access."""
        self._auth[repo_str] = RepoAccess(
            can_write=True, checked_time=datetime.datetime.now()
        )

    def deauthorize_for_repo(self, repo_str: str) -> None:
        """Deny access."""
        self._auth[repo_str] = RepoAccess(
            can_write=False, checked_time=datetime.datetime.now()
        )

    def check_repo(self, repo_str: str) -> Optional[RepoAccess]:
        """This lets us check for the unknown state and expiration too."""
        state = self._auth.get(repo_str)
        if state is None:
            return None
        if datetime.datetime.now() - state.checked_time > self._expiration:
            # Data has expired.  Return None and clear the state.  We
            # need a recheck
            del self._auth[repo_str]
            return None
        return state
