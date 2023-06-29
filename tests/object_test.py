import github_proxy_auth


def test_object_creation() -> None:
    obj = github_proxy_auth.GitHubProxyAuthenticator()
    assert obj is not None
