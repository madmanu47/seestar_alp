"""Local horizon profile: the altitude of the obstructions around the site.

The profile comes from a N.I.N.A. horizon file (``.hrz``): one
``azimuth altitude`` pair per line, in degrees, azimuth measured from north
through east. N.I.N.A. reads this format, and several tools produce it from a
panorama of the site. Between two points the horizon is interpolated
linearly, wrapping at 360 degrees.

The planner draws the profile in AstroMosaic's day chart, and the scheduler
can skip a target hidden behind it (``horizon_skip_hidden_targets``).
"""

import bisect
import os
import threading

import astropy.units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time

from device.config import Config
from device.seestar_util import Util


class HorizonError(ValueError):
    """Raised when a horizon file cannot be read."""


class HorizonProfile:
    """Horizon altitude by azimuth, from a list of (azimuth, altitude) points."""

    def __init__(self, points):
        by_azimuth = {}
        for azimuth, altitude in points:
            azimuth = float(azimuth) % 360.0
            # Two points at the same azimuth: keep the higher, the safer one.
            by_azimuth[azimuth] = max(float(altitude), by_azimuth.get(azimuth, -90.0))
        if not by_azimuth:
            raise HorizonError("the horizon profile has no point")
        self.points = sorted(by_azimuth.items())
        self._azimuths = [azimuth for azimuth, _ in self.points]

    @classmethod
    def parse_hrz(cls, text, source="horizon file"):
        """Profile from the text of a ``.hrz`` file.

        Blank lines and ``#`` comments are ignored; the two values may be
        separated by spaces, tabs, a comma or a semicolon.
        """
        points = []
        for number, line in enumerate(text.splitlines(), start=1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            fields = line.replace(",", " ").replace(";", " ").split()
            try:
                if len(fields) != 2:
                    raise ValueError
                azimuth, altitude = float(fields[0]), float(fields[1])
            except ValueError:
                raise HorizonError(
                    f"{source}, line {number}: expected 'azimuth altitude', got {line!r}"
                ) from None
            if not (0.0 <= azimuth <= 360.0 and -90.0 <= altitude <= 90.0):
                raise HorizonError(
                    f"{source}, line {number}: azimuth must be within 0-360 and "
                    f"altitude within -90-90 degrees, got {line!r}"
                )
            points.append((azimuth, altitude))
        if not points:
            raise HorizonError(f"{source}: no 'azimuth altitude' line")
        return cls(points)

    def altitude_at(self, azimuth):
        """Horizon altitude at ``azimuth``, in degrees."""
        if len(self.points) == 1:
            return self.points[0][1]
        azimuth = float(azimuth) % 360.0
        i = bisect.bisect_right(self._azimuths, azimuth)
        if 0 < i < len(self.points):
            (a0, h0), (a1, h1) = self.points[i - 1], self.points[i]
        else:
            # Between the last point and the first one, across north.
            (a0, h0), (a1, h1) = self.points[-1], self.points[0]
            a1 += 360.0
            if azimuth < a0:
                azimuth += 360.0
        return h0 + (h1 - h0) * (azimuth - a0) / (a1 - a0)

    def step_limits(self, step=5.0):
        """Highest horizon altitude in each step of ``step`` degrees.

        Value ``k`` covers azimuths ``k * step +/- step / 2``, the layout of
        AstroMosaic's ``horizonHard``. The profile being piecewise linear, its
        highest point in a step is at a bound or at one of its points.
        """
        limits = []
        for k in range(round(360.0 / step)):
            low, high = k * step - step / 2, k * step + step / 2
            heights = [self.altitude_at(low), self.altitude_at(high)]
            heights += [
                altitude
                for azimuth, altitude in self.points
                if _in_arc(azimuth, low, high)
            ]
            limits.append(round(max(heights), 2))
        return limits


def _in_arc(azimuth, low, high):
    """Whether ``azimuth`` lies between ``low`` and ``high``, across north if need be."""
    return (azimuth - low) % 360.0 <= high - low


_lock = threading.Lock()
_cache = {"key": None, "profile": None, "error": None}


def configured_profile():
    """``(profile, error)`` for the configured ``horizon_file``.

    ``(None, None)`` when no file is configured. The file is read again when
    its path or modification time changes.
    """
    path = (Config.horizon_file or "").strip()
    if not path:
        return None, None
    try:
        key = (path, os.path.getmtime(path))
    except OSError as e:
        return None, f"{path}: {e.strerror}"
    with _lock:
        if _cache["key"] != key:
            try:
                with open(path, encoding="utf-8-sig") as f:
                    profile, error = HorizonProfile.parse_hrz(f.read(), path), None
            except (OSError, UnicodeDecodeError, HorizonError) as e:
                profile, error = None, str(e)
            _cache.update(key=key, profile=profile, error=error)
        return _cache["profile"], _cache["error"]


def site_location():
    """The site from ``[seestar_initialization]``; ``None`` while it is 0 / 0, unknown."""
    if Config.init_lat == 0 and Config.init_long == 0:
        return None
    return EarthLocation(lat=Config.init_lat * u.deg, lon=Config.init_long * u.deg)


def visibility(coord: SkyCoord, profile, margin=0.0, when=None):
    """Altitude and azimuth of ``coord`` now, against the horizon.

    Without a profile the horizon is flat, at 0 degrees. ``visible`` is true
    when the target is above the horizon plus ``margin``. Returns ``None``
    while the site location is unknown.
    """
    location = site_location()
    if location is None:
        return None
    when = Time.now() if when is None else when
    altaz = coord.transform_to(AltAz(obstime=when, location=location))
    altitude, azimuth = float(altaz.alt.deg), float(altaz.az.deg)
    horizon = profile.altitude_at(azimuth) if profile is not None else 0.0
    return {
        "altitude": round(altitude, 2),
        "azimuth": round(azimuth, 2),
        "horizon": round(horizon, 2),
        "margin": margin,
        "visible": altitude > horizon + margin,
    }


def describe():
    """The ``get_horizon`` action: settings and profile, as plain data."""
    profile, error = configured_profile()
    return {
        "file": Config.horizon_file,
        "error": error,
        "points": [list(point) for point in profile.points] if profile else [],
        "limits_5deg": profile.step_limits() if profile else None,
        "skip_hidden_targets": Config.horizon_skip_hidden_targets,
        "margin": Config.horizon_margin,
    }


def check_target(params):
    """The ``check_target_visibility`` action.

    ``params``: ``ra`` and ``dec`` (decimal hours and degrees, or
    sexagesimal strings) and ``is_j2000`` (default true). Answers for now,
    against the configured profile plus ``horizon_margin``.
    """
    coord = Util.parse_coordinate(
        params.get("is_j2000", True), params["ra"], params["dec"]
    )
    profile, error = configured_profile()
    result = visibility(coord, profile, Config.horizon_margin)
    if result is None:
        return {"error": "site location not set: lat / long are 0"}
    result["horizon_error"] = error
    return result
