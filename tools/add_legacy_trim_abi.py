"""Retired platform mutation entry point; retained to explain migration."""

if __name__ == "__main__":
    raise SystemExit(
        "This platform patch tool is retired. Use device/meizu/m2381/tools/configure_blob_compat.py for the official libbase_shim. "
        "See docs/platform-isolation.md; use apply_platform_patches.py --restore for old checkouts."
    )
