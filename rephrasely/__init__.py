"""Rephrasely application package."""


def create_app(*args, **kwargs):
    """Import the Flask factory lazily so utility modules stay lightweight."""
    from rephrasely.app import create_app as app_factory

    return app_factory(*args, **kwargs)


__all__ = ["create_app"]
