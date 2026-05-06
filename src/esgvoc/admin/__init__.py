"""
esgvoc admin tooling — build, validate, and publish pre-built database artifacts.

Install with:
    pip install esgvoc[admin]   (when extras are configured)

Or use directly via CLI:
    esgvoc admin build --project-path . --universe-repo WCRP-CMIP/WCRP-universe --universe-ref v1.2.0 --output cmip7.db
    esgvoc admin validate cmip7.db
    esgvoc admin test cmip7.db
    esgvoc admin diff baseline.db updated.db
"""
