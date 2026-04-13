"""Domain DTOs shared across dataset preparation, JSON I/O, and search.

Public surface:

- :class:`RawProfile` — corpus / query record before normalization
- :class:`NormalizedProfile` — point in ``[0, 1]^5`` after Min–Max
- :class:`ScalingStats` — per-dimension min/max used for query alignment
- :obj:`ProfileVector` — alias for a length-5 numeric feature vector
"""

from __future__ import annotations

from services.dto.profiles import NormalizedProfile, RawProfile, ScalingStats, ProfileVector

__all__ = ["RawProfile", "NormalizedProfile", "ScalingStats", "ProfileVector"]
