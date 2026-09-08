"""Bounding Box Line Clustering."""
from typing import List, Tuple

def cluster_words_into_lines(boxes: List[Tuple[int, int, int, int, str]], y_tolerance: int = 6) -> List[str]:
    sorted_boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    lines = []
    current_line = []
    current_y = -1

    for x, y, w, h, text in sorted_boxes:
        if current_y == -1 or abs(y - current_y) <= y_tolerance:
            current_line.append(text)
            current_y = y
        else:
            lines.append(" ".join(current_line))
            current_line = [text]
            current_y = y

    if current_line:
        lines.append(" ".join(current_line))
    return lines
