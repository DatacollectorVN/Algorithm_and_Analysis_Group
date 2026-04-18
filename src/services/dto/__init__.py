"""Domain DTOs shared across dataset preparation, JSON I/O, and search.

Public surface:

- :class:`RawProfile` — corpus / query record before normalization
- :class:`NormalizedProfile` — point in ``[0, 1]^14`` after Min–Max and one-hot encoding
- :class:`ScalingStats` — per-dimension min/max used for query alignment (14 dimensions)
- :obj:`ProfileVector` — alias for a variable-length homogeneous float tuple
"""

from __future__ import annotations

from services.dto.profiles import NormalizedProfile, RawProfile, ScalingStats, ProfileVector

__all__ = ["RawProfile", "NormalizedProfile", "ScalingStats", "ProfileVector"]
