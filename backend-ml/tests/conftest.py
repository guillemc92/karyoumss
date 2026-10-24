import cv2
import numpy as np
import pytest


def make_metaphase(n_chromosomes: int = 12, size: tuple[int, int] = (400, 320)) -> np.ndarray:
    """Metafase sintética: fondo blanco con N 'cromosomas' oscuros (elipses)
    bien separados. Autocontenida (no depende del dataset real, CI-safe)."""
    h, w = size
    img = np.full((h, w), 255, dtype=np.uint8)
    rng = np.random.default_rng(42)
    placed = 0
    tries = 0
    centers: list[tuple[int, int]] = []
    while placed < n_chromosomes and tries < 500:
        tries += 1
        cx = int(rng.integers(40, w - 40))
        cy = int(rng.integers(40, h - 40))
        if any(abs(cx - px) < 45 and abs(cy - py) < 45 for px, py in centers):
            continue
        centers.append((cx, cy))
        ang = int(rng.integers(0, 180))
        cv2.ellipse(img, (cx, cy), (8, 22), ang, 0, 360, 40, -1)
        placed += 1
    return img


@pytest.fixture
def synthetic_gray():
    return make_metaphase(12)


@pytest.fixture
def synthetic_png_bytes():
    img = make_metaphase(12)
    ok, buf = cv2.imencode('.png', img)
    assert ok
    return buf.tobytes()
