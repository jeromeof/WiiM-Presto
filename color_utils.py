# ==========================================================
# Color Analysis Utilities for MicroPython
# ==========================================================

from utils import log

def sample_jpeg_colors(jpeg_data, width, height):
    """
    Sample colors from JPEG data by looking at specific byte patterns.
    This is a heuristic approach that samples the raw JPEG bytes.

    Args:
        jpeg_data: Raw JPEG bytes
        width, height: Image dimensions

    Returns:
        dict: {'avg_color': (r, g, b)} or None
    """
    try:
        data_len = len(jpeg_data)
        if data_len < 1000:
            log("JPEG too small for sampling: {} bytes".format(data_len))
            return None

        log("JPEG sampling from {} byte file".format(data_len))

        # Try sampling from multiple regions to find best color representation
        regions = [
            ("start 10-30%", int(data_len * 0.1), int(data_len * 0.3)),
            ("middle 40-60%", int(data_len * 0.4), int(data_len * 0.6)),
            ("end 70-90%", int(data_len * 0.7), int(data_len * 0.9)),
        ]

        all_samples = []

        for region_name, start_pos, end_pos in regions:
            sample_size = min(300, end_pos - start_pos)
            r_sum, g_sum, b_sum = 0, 0, 0
            sample_count = 0

            # Sample every 3rd byte as potential RGB values
            for i in range(start_pos, start_pos + sample_size, 3):
                if i + 2 < data_len:
                    r = jpeg_data[i]
                    g = jpeg_data[i + 1]
                    b = jpeg_data[i + 2]

                    # Filter out obvious non-color bytes (0x00, 0xFF markers)
                    if not (r in (0, 255) and g in (0, 255) and b in (0, 255)):
                        r_sum += r
                        g_sum += g
                        b_sum += b
                        sample_count += 1

            if sample_count > 10:
                avg_r = r_sum // sample_count
                avg_g = g_sum // sample_count
                avg_b = b_sum // sample_count

                log("  {}: RGB({},{},{}) from {} samples".format(
                    region_name, avg_r, avg_g, avg_b, sample_count))

                all_samples.append((avg_r, avg_g, avg_b, sample_count))

        # Use weighted average of all regions
        if all_samples:
            total_weight = sum(s[3] for s in all_samples)
            final_r = sum(s[0] * s[3] for s in all_samples) // total_weight
            final_g = sum(s[1] * s[3] for s in all_samples) // total_weight
            final_b = sum(s[2] * s[3] for s in all_samples) // total_weight

            log("JPEG final color: RGB({},{},{}) from {} total samples".format(
                final_r, final_g, final_b, total_weight))

            return {'avg_color': (final_r, final_g, final_b)}
        else:
            log("JPEG sampling: insufficient samples")

    except Exception as e:
        log("JPEG color sampling error: {}".format(e))

    return None

def sample_pixels(display, x, y, width, height, sample_count=50):
    """
    Sample random pixels from a region of the display.

    Args:
        display: PicoGraphics display object
        x, y: Top-left corner of region
        width, height: Size of region
        sample_count: Number of pixels to sample

    Returns:
        list: List of (r, g, b) tuples
    """
    import random

    samples = []

    # Try different methods to read pixels
    for _ in range(sample_count):
        px = x + random.randint(0, width - 1)
        py = y + random.randint(0, height - 1)

        # Clamp to display bounds
        px = max(0, min(px, display.get_bounds()[0] - 1))
        py = max(0, min(py, display.get_bounds()[1] - 1))

        # Try multiple methods to read pixel
        try:
            # Method 1: pixel() method
            if hasattr(display, 'pixel'):
                color = display.pixel(px, py)
                if color is not None:
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                    samples.append((r, g, b))
                    continue
        except:
            pass

        try:
            # Method 2: get_pixel() method (some displays)
            if hasattr(display, 'get_pixel'):
                color = display.get_pixel(px, py)
                if color is not None:
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                    samples.append((r, g, b))
                    continue
        except:
            pass

    log("Sampled {} pixels".format(len(samples)))
    return samples

def average_color(colors):
    """
    Calculate average RGB color from a list of colors.

    Args:
        colors: List of (r, g, b) tuples

    Returns:
        tuple: (r, g, b) average color
    """
    if not colors:
        return (0, 0, 0)

    r_sum = sum(c[0] for c in colors)
    g_sum = sum(c[1] for c in colors)
    b_sum = sum(c[2] for c in colors)

    count = len(colors)
    return (
        r_sum // count,
        g_sum // count,
        b_sum // count
    )

def calculate_luminance(r, g, b):
    """
    Calculate perceived brightness of an RGB color.
    Uses standard luminance formula.

    Args:
        r, g, b: Color components (0-255)

    Returns:
        float: Luminance value (0-255)
    """
    # Perceived brightness formula
    return (0.299 * r) + (0.587 * g) + (0.114 * b)

def get_contrast_color(r, g, b):
    """
    Determine if white or black text provides better contrast.

    Args:
        r, g, b: Background color

    Returns:
        tuple: (r, g, b) for text color (white or black)
    """
    luminance = calculate_luminance(r, g, b)

    # If background is dark (luminance < 128), use white text
    # If background is bright, use black text
    if luminance < 128:
        return (255, 255, 255)  # White text
    else:
        return (0, 0, 0)  # Black text

def adjust_color_for_visibility(r, g, b, min_saturation=50):
    """
    Adjust a color to ensure it's visible and not too gray.
    Increases saturation if needed.

    Args:
        r, g, b: Original color
        min_saturation: Minimum saturation to ensure

    Returns:
        tuple: (r, g, b) adjusted color
    """
    # Calculate saturation
    max_val = max(r, g, b)
    min_val = min(r, g, b)

    if max_val == 0:
        log("Color adjustment: black -> gray({})".format(min_saturation))
        return (min_saturation, min_saturation, min_saturation)

    saturation = (max_val - min_val) / max_val * 255
    log("Color adjustment: RGB({},{},{}) saturation={:.0f}".format(r, g, b, saturation))

    # If too gray, boost the dominant color
    if saturation < min_saturation:
        original = (r, g, b)
        # Find dominant channel
        if r >= g and r >= b:
            r = min(255, r + min_saturation)
            log("  Boosting red: {} -> {}".format(original[0], r))
        elif g >= b:
            g = min(255, g + min_saturation)
            log("  Boosting green: {} -> {}".format(original[1], g))
        else:
            b = min(255, b + min_saturation)
            log("  Boosting blue: {} -> {}".format(original[2], b))

    return (r, g, b)

def get_album_art_colors(display, text_region_y, text_region_height):
    """
    Sample colors from the album art in the text overlay region.

    Args:
        display: PicoGraphics display object
        text_region_y: Y position where text will be placed
        text_region_height: Height of text region

    Returns:
        dict: {
            'background': (r, g, b) for text backgrounds,
            'text': (r, g, b) for text color
        }
    """
    width, height = display.get_bounds()

    # Sample pixels from the bottom region where text will appear
    log("Sampling album art colors from region y={} h={}".format(
        text_region_y, text_region_height))

    samples = sample_pixels(
        display,
        0, text_region_y,
        width, text_region_height,
        sample_count=30  # Keep it light for performance
    )

    if not samples:
        log("No color samples, using default black/white")
        return {
            'background': (0, 0, 0),
            'text': (255, 255, 255)
        }

    # Calculate average color
    avg_color = average_color(samples)
    log("Average color: RGB({}, {}, {})".format(*avg_color))

    # Adjust for visibility
    bg_color = adjust_color_for_visibility(*avg_color)
    log("Adjusted background: RGB({}, {}, {})".format(*bg_color))

    # Determine contrasting text color
    text_color = get_contrast_color(*bg_color)
    log("Text color: RGB({}, {}, {})".format(*text_color))

    return {
        'background': bg_color,
        'text': text_color
    }
