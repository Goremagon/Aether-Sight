"""Computer vision utilities for detecting and warping Magic cards."""

from typing import Optional, Tuple

import cv2
import numpy as np


class CardDetector:
    """Detect and warp card-shaped objects in video frames."""

    def __init__(self, min_area: int = 5000) -> None:
        """Initialize the detector.

        Args:
            min_area: Minimum contour area to consider as a potential card.
        """
        self.min_area = min_area

    def detect_card(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Detect the largest quadrilateral contour representing a card.

        Args:
            frame: BGR image array from OpenCV.

        Returns:
            The approximated contour with four points if found, otherwise None.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 75, 200)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        largest_contour = None
        largest_area = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            if len(approx) == 4 and area > largest_area:
                largest_area = area
                largest_contour = approx
        return largest_contour

    def get_warp(
        self, frame: np.ndarray, contour: np.ndarray, output_size: Tuple[int, int] = (448, 320)
    ) -> Optional[np.ndarray]:
        """Perform a perspective transform to obtain a top-down view of the card.

        Args:
            frame: BGR image array from OpenCV.
            contour: Four-point contour approximating the card.
            output_size: Desired output size (width, height) for the warped image.

        Returns:
            Warped BGR image of the card if successful, otherwise None.
        """
        if contour is None or len(contour) != 4:
            return None
        points = contour.reshape(4, 2).astype("float32")
        ordered = self._order_points(points)
        width, height = output_size
        destination = np.array(
            [
                [0, 0],
                [width - 1, 0],
                [width - 1, height - 1],
                [0, height - 1],
            ],
            dtype="float32",
        )
        matrix = cv2.getPerspectiveTransform(ordered, destination)
        warped = cv2.warpPerspective(frame, matrix, (width, height))
        return warped

    @staticmethod
    def _order_points(points: np.ndarray) -> np.ndarray:
        """Order contour points as top-left, top-right, bottom-right, bottom-left."""
        ordered = np.zeros((4, 2), dtype="float32")
        sum_points = points.sum(axis=1)
        ordered[0] = points[np.argmin(sum_points)]
        ordered[2] = points[np.argmax(sum_points)]

        diff_points = np.diff(points, axis=1)
        ordered[1] = points[np.argmin(diff_points)]
        ordered[3] = points[np.argmax(diff_points)]
        return ordered
