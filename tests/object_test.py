import giftless_github_proxy_auth


def test_object_creation() -> None:
    obj = giftless_github_proxy_auth.GiftlessGitHubProxyAuthenticator()
    assert obj is not None
