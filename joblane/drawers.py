from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .lane_packs import load_lane_packs


@dataclass(frozen=True)
class DrawerRef:
    lane_id: str
    drawer: str
    path: Path
    exists: bool

    def to_dict(self) -> dict:
        return {
            "lane_id": self.lane_id,
            "drawer": self.drawer,
            "path": str(self.path),
            "exists": self.exists,
        }


class DrawerManager:
    def __init__(self, root: Path | str, *, lanes_root: Path | str = "lanes") -> None:
        self.root = Path(root)
        self.lanes_root = lanes_root

    def refs(self) -> list[DrawerRef]:
        refs = []
        for pack in load_lane_packs(self.lanes_root).values():
            for drawer in pack.drawers:
                path = self.root / "lanes" / pack.lane_id / drawer
                refs.append(
                    DrawerRef(
                        lane_id=pack.lane_id,
                        drawer=drawer,
                        path=path,
                        exists=path.exists(),
                    )
                )
        return refs

    def ensure(self) -> list[DrawerRef]:
        for ref in self.refs():
            ref.path.mkdir(parents=True, exist_ok=True)
        return self.refs()
