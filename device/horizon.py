"""Local horizon profile: the altitude of the obstructions around the site.

The profile comes from a N.I.N.A. horizon file (``.hrz``): one
``azimuth altitude`` pair per line, in degrees, azimuth measured from north
through east. N.I.N.A. reads this format, and several tools produce it from a
panorama of the site. Between two points the horizon is interpolated
linearly, wrapping at 360 degrees.

The planner draws the profile in AstroMosaic's day chart, and the scheduler
can skip a target hidden behind it (``horizon_skip_hidden_targets``). The
Horizon page makes one from a 360-degree panorama, in the browser.
"""

import bisect
import json
import math
import os
import threading

from astropy.coordinates import FK5, SkyCoord
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
    """``(latitude, longitude)`` from ``[seestar_initialization]``.

    ``None`` while both are 0, the value that stands for an unknown site.
    """
    if Config.init_lat == 0 and Config.init_long == 0:
        return None
    return float(Config.init_lat), float(Config.init_long)


def altaz(coord: SkyCoord, latitude, longitude, when: Time):
    """Altitude and azimuth of ``coord`` at ``when``, in degrees.

    Hour angle from the mean sidereal time, on coordinates of the date: good
    to a few hundredths of a degree, more than a horizon check needs. It
    avoids astropy's AltAz frame, which needs Earth orientation (IERS) tables
    less than 30 days old and raises on an install that cannot download them.
    Refraction is left out: it lifts a low target by half a degree at most,
    so the check errs on the hidden side.
    """
    of_date = coord.transform_to(FK5(equinox=when))
    return _altaz_of_date(of_date.ra.deg, of_date.dec.deg, latitude, longitude, when)


def sun_altaz(latitude, longitude, when: Time):
    """Altitude and azimuth of the Sun at ``when``, in degrees.

    Low-precision formulae of the Astronomical Almanac, good to a hundredth of
    a degree between 1950 and 2050: enough to orient a panorama on the Sun.
    Geometric position: refraction would lift it by 0.03 degree at 25 degrees.
    """
    days = when.utc.jd - 2451545.0
    mean_longitude = 280.460 + 0.9856474 * days
    anomaly = math.radians(357.528 + 0.9856003 * days)
    ecliptic = math.radians(
        mean_longitude + 1.915 * math.sin(anomaly) + 0.020 * math.sin(2 * anomaly)
    )
    obliquity = math.radians(23.439 - 0.0000004 * days)
    ra = math.atan2(math.cos(obliquity) * math.sin(ecliptic), math.cos(ecliptic))
    dec = math.asin(math.sin(obliquity) * math.sin(ecliptic))
    return _altaz_of_date(
        math.degrees(ra), math.degrees(dec), latitude, longitude, when
    )


def _altaz_of_date(ra_deg, dec_deg, latitude, longitude, when: Time):
    """Altitude and azimuth from right ascension and declination of the date."""
    days = when.utc.jd - 2451545.0
    sidereal = (280.46061837 + 360.98564736629 * days + longitude) % 360.0
    hour_angle = math.radians(sidereal - ra_deg)
    dec, lat = math.radians(dec_deg), math.radians(latitude)
    altitude = math.asin(
        math.sin(dec) * math.sin(lat)
        + math.cos(dec) * math.cos(lat) * math.cos(hour_angle)
    )
    azimuth = math.atan2(
        -math.cos(dec) * math.sin(hour_angle),
        math.sin(dec) * math.cos(lat)
        - math.cos(dec) * math.sin(lat) * math.cos(hour_angle),
    )
    return math.degrees(altitude), math.degrees(azimuth) % 360.0


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
    altitude, azimuth = altaz(coord, *location, when)
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


# Profile made from a panorama on the Horizon page, saved next to config.toml.
PANORAMA_HRZ = "horizon.hrz"
PANORAMA_JSON = "horizon.horizon.json"


def save_panorama_profile(hrz_text, horizon_json=None):
    """Save a profile made from a panorama, and make it the configured horizon.

    ``hrz_text`` is the ``.hrz`` the page exported; ``horizon_json``, when
    given, the MMhorizon ``.horizon.json`` it came from, kept beside it as a
    record of the photo and of how north was set. Both go next to
    config.toml, and ``horizon_file`` then points to the ``.hrz``; a file
    configured before is left in place. Returns ``(path, previous_file,
    profile)``. Raises ``HorizonError`` on an invalid profile.
    """
    profile = HorizonProfile.parse_hrz(hrz_text, "uploaded profile")
    if horizon_json is not None:
        try:
            record = json.loads(horizon_json)
        except ValueError as e:
            raise HorizonError(f"uploaded .horizon.json: {e}") from None
        if not isinstance(record, dict) or record.get("format") != "horizon":
            raise HorizonError("uploaded .horizon.json: not an MMhorizon file")
    folder = os.path.dirname(Config.path_to_dat)
    path = os.path.join(folder, PANORAMA_HRZ)
    _write_atomic(path, hrz_text)
    if horizon_json is not None:
        _write_atomic(os.path.join(folder, PANORAMA_JSON), horizon_json)
    previous = Config.horizon_file
    Config.set_toml("seestar_initialization", "horizon_file", path)
    Config.save_toml()
    Config.load_toml()
    return path, previous, profile


def _write_atomic(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)
