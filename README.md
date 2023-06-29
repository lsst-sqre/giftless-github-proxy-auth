# giftless-github-proxy-auth

This is a [Giftless](https://giftless.datopian.com) [authentication
module](https://giftless.datopian.com/en/latest/auth-providers.html#understanding-authentication-and-authorization-providers)
designed to check whether a user has push permissions to the GitHub
repository they're trying to store Git LFS assets for.

# Installing

`pip install giftless-github-proxy-auth`, or check out the repository and do a
`pip install -e .`

It's only really useful in the context of a Giftless authenticator,
though, so in practice you probably just want to build the giftless
OCI image with this module included.

# Limitations

This only works with:
1. GitHub repositories
2. With https, not ssh, as the access methods
3. With classic Personal Access Tokens

This is because each repository provider has its own method of
authentication, because ssh would require our proxy to know users'
private keys, and because fine-grained tokens can only grant access to
repositories the user owns, which in the context of Rubin Observatory is
unlikely.


