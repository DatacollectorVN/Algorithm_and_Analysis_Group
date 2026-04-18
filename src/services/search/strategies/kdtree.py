"""Five-dimensional KD-tree with weighted squared-distance k-NN search."""

from __future__ import annotations

from dataclasses import dataclass

from services.constants import KD_TREE_LB_EPS, VECTOR_DIM
from services.dataset import Corpuses
from services.dto import VectorizedProfile
from services.helper import (
    ValidationError,
    bbox_of_point,
    union_bbox,
    weighted_sq_dist_query_to_box,
)
from services.search.distance import weighted_squared_distance
from services.search.strategies.base import SearchStrategy
from services.search.topk import TopKManager


@dataclass(slots=True)
class _KDNode:
    """KD-tree node with axis-aligned bounding box of its subtree."""

    point: VectorizedProfile
    axis: int
    left: _KDNode | None
    right: _KDNode | None
    bbox_lo: tuple[float, ...]
    bbox_hi: tuple[float, ...]


def _merge_node_bbox(
    point_vec: tuple[float, ...],
    left: _KDNode | None,
    right: _KDNode | None,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    lo, hi = bbox_of_point(point_vec)
    if left is not None:
        lo, hi = union_bbox(lo, hi, left.bbox_lo, left.bbox_hi)
    if right is not None:
        lo, hi = union_bbox(lo, hi, right.bbox_lo, right.bbox_hi)
    return lo, hi


def _build_kdtree(points: list[VectorizedProfile], depth: int) -> _KDNode | None:
    if not points:
        return None
    if len(points) == 1:
        p = points[0]
        lo, hi = bbox_of_point(p.vector)
        return _KDNode(p, depth % VECTOR_DIM, None, None, lo, hi)
    axis = depth % VECTOR_DIM
    sp = sorted(points, key=lambda x: x.vector[axis])
    mid = len(sp) // 2
    node_point = sp[mid]
    left_pts = sp[:mid]
    right_pts = sp[mid + 1 :]
    left = _build_kdtree(left_pts, depth + 1)
    right = _build_kdtree(right_pts, depth + 1)
    lo, hi = _merge_node_bbox(node_point.vector, left, right)
    return _KDNode(node_point, axis, left, right, lo, hi)


def _search_knn(
    node: _KDNode | None,
    query: tuple[float, ...],
    weights: tuple[float, ...],
    k: int,
    mgr: TopKManager,
) -> None:
    if node is None:
        return
    d = weighted_squared_distance(query, node.point.vector, weights)
    mgr.push(d, node.point.profile_id, k)

    axis = node.axis
    delta = query[axis] - node.point.vector[axis]
    near, far = (node.left, node.right) if delta < 0 else (node.right, node.left)

    _search_knn(near, query, weights, k, mgr)

    if far is not None:
        if mgr.size < k:
            _search_knn(far, query, weights, k, mgr)
        else:
            lb = weighted_sq_dist_query_to_box(query, weights, far.bbox_lo, far.bbox_hi)
            if lb <= mgr.worst_distance() + KD_TREE_LB_EPS:
                _search_knn(far, query, weights, k, mgr)


class KDTreeSearcher(SearchStrategy):
    """Spatial partitioning index; average-case sublinear pruning vs baseline."""

    __slots__ = ("_root",)

    def __init__(self, corpuses: Corpuses) -> None:
        super().__init__(corpuses)
        if not corpuses.vectorized_profiles:
            raise ValidationError("corpus must be non-empty for KDTreeSearcher")
        self._root: _KDNode | None = _build_kdtree(list(corpuses.vectorized_profiles), 0)

    def search(
        self,
        query_vector: tuple[float, ...],
        weights: tuple[float, ...],
        k: int,
    ) -> list[tuple[int, float]]:
        if k < 1:
            raise ValidationError("k must be at least 1")
        if self._root is None:
            raise ValidationError("KD-tree not built")
        mgr = TopKManager()
        _search_knn(self._root, query_vector, weights, k, mgr)
        return mgr.finalize()
