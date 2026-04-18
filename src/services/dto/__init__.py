"""Domain DTOs shared across dataset preparation, JSON I/O, and search.

Public surface:

- :class:`Profile` — corpus row before normalization (requires ``profile_id``)
- :class:`QProfile` — query ``profile`` object (no ``profile_id``)
- :class:`QueryProfile` — validated query JSON (``profile``, ``weights``, ``k``)
- :class:`VectorizedProfile` — point in ``[0, 1]^14`` after Min–Max and one-hot encoding (``profile_id``: ``int``)
- :class:`VectorizedQueryProfile` — normalized query vector, weights, and ``k``
- :class:`ScalingStats` — per-dimension min/max used for query alignment (14 dimensions)
- :obj:`ProfileVector` — alias for a variable-length homogeneous float tuple
"""

from __future__ import annotations

from services.dto.profiles import (
    Profile,
    ProfileVector,
    QProfile,
    QueryProfile,
    ScalingStats,
    VectorizedProfile,
    VectorizedQueryProfile,
    TopKResult,
)

__all__ = [
    "Profile",
    "QProfile",
    "QueryProfile",
    "VectorizedProfile",
    "VectorizedQueryProfile",
    "ScalingStats",
    "ProfileVector",
    "TopKResult",
]
