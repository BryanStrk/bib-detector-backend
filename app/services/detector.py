"""Pluggable bib-detection pipeline.

Two interchangeable backends produce the same ``Detection`` schema:

* **YOLO + EasyOCR** (when ``MODEL_PATH`` is set): a YOLO model locates bib
  regions, each region is cropped, and EasyOCR reads the number from the crop.
* **EasyOCR only** (default MVP): EasyOCR runs on the whole image and numeric
  results (1-5 digits) become detections.

Heavy models (EasyOCR reader, YOLO weights) are expensive to load, so the
``BibDetector`` is built lazily and reused as a process-wide singleton.
"""

from __future__ import annotations

import io
import logging
import re
from functools import lru_cache

import numpy as np
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings, get_settings
from app.core.exceptions import DetectorError
from app.schemas.detection import Detection

logger = logging.getLogger(__name__)

# A valid bib number is 1-5 digits (optionally surrounded by OCR noise we strip).
_BIB_PATTERN = re.compile(r"^\d{1,5}$")


def _is_bib_number(text: str) -> bool:
    """Return True if ``text`` (after stripping) looks like a bib number."""
    return bool(_BIB_PATTERN.match(text.strip()))


def _polygon_to_xywh(polygon: list[list[float]]) -> list[float]:
    """Convert an EasyOCR 4-point polygon to an ``[x, y, w, h]`` box."""
    xs = [float(point[0]) for point in polygon]
    ys = [float(point[1]) for point in polygon]
    x_min, y_min = min(xs), min(ys)
    return [x_min, y_min, max(xs) - x_min, max(ys) - y_min]


class BibDetector:
    """Detects athlete bib numbers in an image.

    The active backend is chosen from ``Settings`` at construction time. Models
    are loaded lazily on first use to keep startup fast.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._reader = None  # EasyOCR reader, loaded lazily.
        self._yolo = None  # Ultralytics YOLO model, loaded lazily.

    @property
    def backend(self) -> str:
        """Human-readable name of the active detection backend."""
        return "yolo+easyocr" if self._settings.model_path else "easyocr"

    # -- Lazy model loaders ------------------------------------------------

    def _get_reader(self):
        """Lazily construct and cache the EasyOCR reader (English, CPU)."""
        if self._reader is None:
            import easyocr  # Imported here so app import stays light.

            logger.info("Loading EasyOCR reader...")
            self._reader = easyocr.Reader(["en"], gpu=False)
        return self._reader

    def _get_yolo(self):
        """Lazily load the YOLO model from ``MODEL_PATH``."""
        if self._yolo is None:
            from ultralytics import YOLO

            logger.info("Loading YOLO model from %s", self._settings.model_path)
            self._yolo = YOLO(self._settings.model_path)
        return self._yolo

    # -- Public API --------------------------------------------------------

    def detect(self, image_bytes: bytes) -> list[Detection]:
        """Run the configured pipeline and return filtered detections.

        Args:
            image_bytes: Raw bytes of a JPEG or PNG image.

        Returns:
            Detections with confidence >= ``MIN_CONFIDENCE``.

        Raises:
            DetectorError: If the image cannot be decoded or inference fails.
        """
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except (UnidentifiedImageError, OSError) as exc:
            raise DetectorError("Could not decode the uploaded image.") from exc

        array = np.array(image)

        try:
            if self._settings.model_path:
                detections = self._detect_with_yolo(array)
            else:
                detections = self._detect_with_ocr(array)
        except DetectorError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize to DetectorError
            raise DetectorError("Detection pipeline failed.") from exc

        threshold = self._settings.min_confidence
        return [d for d in detections if d.confidence >= threshold]

    # -- Backends ----------------------------------------------------------

    def _detect_with_ocr(self, array: np.ndarray) -> list[Detection]:
        """MVP path: read text from the whole image, keep numeric results."""
        results = self._get_reader().readtext(array)
        detections: list[Detection] = []
        for polygon, text, confidence in results:
            if not _is_bib_number(text):
                continue
            detections.append(
                Detection(
                    bib_number=text.strip(),
                    confidence=float(confidence),
                    bbox=_polygon_to_xywh(polygon),
                )
            )
        return detections

    def _detect_with_yolo(self, array: np.ndarray) -> list[Detection]:
        """YOLO path: detect bib regions, then OCR each crop for its number."""
        reader = self._get_reader()
        model = self._get_yolo()
        detections: list[Detection] = []

        for result in model(array, verbose=False):
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
                det_conf = float(box.conf[0])
                crop = array[int(y1) : int(y2), int(x1) : int(x2)]
                if crop.size == 0:
                    continue

                bib_number, ocr_conf = self._read_number_from_crop(reader, crop)
                if bib_number is None:
                    continue

                # Combine region confidence and OCR confidence.
                detections.append(
                    Detection(
                        bib_number=bib_number,
                        confidence=det_conf * ocr_conf,
                        bbox=[x1, y1, x2 - x1, y2 - y1],
                    )
                )
        return detections

    @staticmethod
    def _read_number_from_crop(reader, crop: np.ndarray) -> tuple[str | None, float]:
        """Return the best numeric reading from a cropped bib region."""
        best_text: str | None = None
        best_conf = 0.0
        for _polygon, text, confidence in reader.readtext(crop):
            if _is_bib_number(text) and confidence >= best_conf:
                best_text = text.strip()
                best_conf = float(confidence)
        return best_text, best_conf


@lru_cache
def get_detector() -> BibDetector:
    """Return the process-wide ``BibDetector`` singleton (FastAPI dependency)."""
    return BibDetector(get_settings())
