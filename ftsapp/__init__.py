"""Support package for the FTS review tool.

Split by responsibility so each piece can be read on its own:

    paths      where the analysis lives; nothing else
    pipeline   imports the analysis scripts and re-exports their thresholds
    freshness  refuses to render anything built from a superseded extract
    data       cached readers for the workbooks
    evidence   the per-work-order rows behind one recommendation
    charts     the distribution chart
    text       the prose the pages share
"""
