from pathlib import Path

WALLPAPER_TILES = Path(__file__).parent / "qte_tiles.png"
WALLPAPER_TRIANGLES = Path(__file__).parent / "qte_triangles.png"

__all__ = ["WALLPAPER_TILES", "WALLPAPER_TRIANGLES"]


def __dir__():
    return sorted(__all__)
