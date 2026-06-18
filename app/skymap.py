import math

VIEWBOX_SIZE = 400
CX = VIEWBOX_SIZE / 2        # 200.0
CY = VIEWBOX_SIZE / 2        # 200.0
R  = VIEWBOX_SIZE / 2 - 10   # 190.0  (10px margin inside circle)


def az_alt_to_xy(az_deg: float, alt_deg: float) -> tuple[float, float]:
    """Project alt/az to SVG x,y. Zenith → center; horizon → edge circle."""
    r = (90.0 - alt_deg) / 90.0 * R
    az_rad = math.radians(az_deg)
    x = CX + r * math.sin(az_rad)
    y = CY - r * math.cos(az_rad)
    return x, y


def star_radius(magnitude: float) -> float:
    return max(0.5, 3.5 - magnitude * 0.5)


def generate_skymap(
    stars: list[dict],
    const_lines: list[dict],
) -> str:
    """
    stars:       [{"alt": float, "az": float, "magnitude": float, "hip_id": int}, ...]
    const_lines: [{"hip_a": int, "hip_b": int, "constellation": str}, ...]
    Returns a self-contained SVG string.
    """
    hip_xy: dict[int, tuple[float, float]] = {
        s["hip_id"]: az_alt_to_xy(s["az"], s["alt"]) for s in stars
    }

    # figure-star membership: hip_id -> sorted set of constellation names
    fig_members: dict[int, set[str]] = {}
    lines_svg = []
    for seg in const_lines:
        a, b = seg["hip_a"], seg["hip_b"]
        name = seg.get("constellation")
        if a in hip_xy and b in hip_xy:
            x1, y1 = hip_xy[a]
            x2, y2 = hip_xy[b]
            if name:
                lines_svg.append(
                    f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                    f'data-constellation="{name}" '
                    f'stroke="#6b6256" stroke-width="0.8" stroke-opacity="0.7"/>'
                )
                fig_members.setdefault(a, set()).add(name)
                fig_members.setdefault(b, set()).add(name)
            else:
                lines_svg.append(
                    f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                    f'stroke="#6b6256" stroke-width="0.8" stroke-opacity="0.7"/>'
                )

    stars_svg = []
    for s in stars:
        x, y = hip_xy[s["hip_id"]]
        r = star_radius(s["magnitude"])
        members = fig_members.get(s["hip_id"])
        if members:
            tag = " ".join(sorted(members))
            stars_svg.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
                f'data-constellation="{tag}" class="figstar" '
                f'fill="#ece7da" fill-opacity="0.95"/>'
            )
        else:
            stars_svg.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
                f'fill="#cfc8b8" fill-opacity="0.85"/>'
            )

    cardinals = [("N", 0), ("E", 90), ("S", 180), ("W", 270)]
    cardinal_svg = []
    for label, az in cardinals:
        x, y = az_alt_to_xy(az, 0.0)
        scale = (R + 12) / R
        lx = CX + (x - CX) * scale
        ly = CY + (y - CY) * scale
        cardinal_svg.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" fill="#8a8276" font-size="10" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-family="serif">{label}</text>'
        )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {VIEWBOX_SIZE} {VIEWBOX_SIZE}" '
        f'width="{VIEWBOX_SIZE}" height="{VIEWBOX_SIZE}" style="background:#08080a">',
        f'<circle cx="{CX:.1f}" cy="{CY:.1f}" r="{R:.1f}" fill="#08080a" '
        f'stroke="#2a2a2e" stroke-width="1"/>',
        *lines_svg,
        *stars_svg,
        *cardinal_svg,
        "</svg>",
    ]
    return "\n".join(parts)
