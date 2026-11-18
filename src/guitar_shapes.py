"""Standard tuning, low string first. None means mute the string."""
TUNING = (40, 45, 50, 55, 59, 64)
OPEN = {
    (0, 4): (None, 3, 2, 0, 1, 0), (2, 4): (None, None, 0, 2, 3, 2),
    (2, 3): (None, None, 0, 2, 3, 1), (7, 4): (3, 2, 0, 0, 0, 3),
}


def grips(chord):
    """Open shapes and movable E/A shapes for major, minor and diminished triads."""
    third = (chord.pcs[1] - chord.root) % 12
    fifth = (chord.pcs[2] - chord.root) % 12
    shapes = []
    if fifth == 6:
        # Movable diminished triad on the inner four strings, root on string 5.
        fret = (chord.root - 9) % 12 or 12
        shapes.append((None, fret, fret+1, fret+2, fret+1, None))
    else:
        if (chord.root, third) in OPEN:
            shapes.append(OPEN[chord.root, third])
        e = (chord.root - 4) % 12
        a = (chord.root - 9) % 12
        shapes.extend([(e, e+2, e+2, e+third-3, e, e),
                       (None, a, a+2, a+2, a+third-2, a)])
    return [tuple(p+f for p, f in zip(TUNING, shape) if f is not None)
            for shape in shapes]
