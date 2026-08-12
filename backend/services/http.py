"""
Shared aiohttp session factory with a working certificate bundle.

macOS builds of Python from python.org ship no root certificates. OpenSSL's
default search paths are empty until the bundled "Install Certificates.command"
is run, so every aiohttp HTTPS request fails with:

    ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED]
    certificate verify failed: unable to get local issuer certificate

The Anthropic SDK is unaffected because it runs on httpx, which trusts certifi
by default — which is why Claude calls worked while Mission Control sync,
vidIQ, and ElevenLabs all failed on the same machine.

Pointing aiohttp at certifi as well makes the app work on a stock install,
without the operator having to know that script exists.

Use `from services.http import session` and `async with session() as s:` in
place of `aiohttp.ClientSession()`.
"""

import ssl

import aiohttp

try:
    import certifi
    _CAFILE: str | None = certifi.where()
except ImportError:          # certifi absent — fall back to system defaults
    _CAFILE = None


def ssl_context() -> ssl.SSLContext | None:
    """Verified SSL context using certifi's CA bundle, or None to use the
    system default when certifi isn't installed."""
    if not _CAFILE:
        return None
    return ssl.create_default_context(cafile=_CAFILE)


def session(**kwargs) -> aiohttp.ClientSession:
    """aiohttp.ClientSession that can actually verify HTTPS on macOS.

    Certificate verification stays ON — this fixes trust, it does not bypass
    it. Never replace this with ssl=False.
    """
    if "connector" not in kwargs:
        ctx = ssl_context()
        if ctx is not None:
            kwargs["connector"] = aiohttp.TCPConnector(ssl=ctx)
    return aiohttp.ClientSession(**kwargs)
