"""Adaptive Image Binarization Utilities."""

def otsu_threshold(histogram: list) -> int:
    total = sum(histogram)
    sum_b = 0
    w_b = 0
    maximum = 0.0
    threshold = 0
    sum_total = sum(i * histogram[i] for i in range(256))

    for i in range(256):
        w_b += histogram[i]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += i * histogram[i]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        between = w_b * w_f * ((m_b - m_f) ** 2)
        if between > maximum:
            maximum = between
            threshold = i
    return threshold
