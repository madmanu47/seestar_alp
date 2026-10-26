import {
  hasUtcOffset,
  horizonLineFromSun,
  photoPoint,
  photoTimeUtc,
  profilePoints,
  summary,
} from "../public/horizon_panorama_core.js";

describe("horizon_panorama_core.js", () => {
  it("moves the horizon line so that the Sun's row has the Sun's altitude", () => {
    // Under a horizon at row 1400, altitude 26.3 falls on row 404; the Sun is
    // seen on row 433: the horizon is 29 rows lower.
    expect(horizonLineFromSun(433, 404, 1400)).toBe(1429);
  });

  it("reads the photo date as UTC, with or without offset", () => {
    expect(photoTimeUtc("2026-10-23T15:59:17+02:00")).toBe("2026-10-23T13:59:17.000Z");
    expect(photoTimeUtc("2026-10-23T15:59:17")).toBe(new Date(2026, 9, 23, 15, 59, 17).toISOString());
    expect(photoTimeUtc(null)).toBeNull();
    expect(photoTimeUtc("not a date")).toBeNull();
    expect(hasUtcOffset("2026-10-23T15:59:17+02:00")).toBe(true);
    expect(hasUtcOffset("2026-10-23T15:59:17Z")).toBe(true);
    expect(hasUtcOffset("2026-10-23T15:59:17")).toBe(false);
  });

  it("maps a click on the scaled canvas to photo pixels", () => {
    // 3600 x 795 preview of a 12672 x 2800 photo, drawn 1200 px wide at (10, 50).
    const rect = { left: 10, top: 50, width: 1200, height: 265 };
    const point = photoPoint(610, 182.5, rect, 3600, 795, 12672, 2800);
    expect(point.column).toBeCloseTo(6336, 6);
    expect(point.row).toBeCloseTo(1400, 6);
  });

  it("draws the profile like the Planning page's Horizon card", () => {
    const altitudes = Array.from({ length: 360 }, (_, azimuth) => (azimuth === 90 ? 25.5 : 10));
    altitudes[200] = null; // outside the panorama
    altitudes[300] = 95; // clamped to the 0-90 scale
    const points = profilePoints(altitudes).split(" ");
    expect(points[0]).toBe("0,90");
    expect(points[1]).toBe("0,80");
    expect(points[91]).toBe("90,64.5");
    expect(points[201]).toBe("200,90");
    expect(points[301]).toBe("300,0");
    expect(points.slice(-2)).toEqual(["360,80", "360,90"]);
  });

  it("summarises the panorama in English", () => {
    const text = summary({
      largeur: 12672,
      hauteur: 2800,
      projection: "cylindrique",
      couverture_deg: 360,
      couverture_methode: "supposee",
      champ_vertical_deg: [-34.207, 35.319],
      orientation: "paysage",
      objectif: "ultra-grand-angle",
      au_dela_du_champ: 3,
      gpano_ecarte: "GPano écarté : …",
    });
    expect(text).toBe(
      "12672 × 2800 px · cylindrical · 360° of azimuth (assumed full turn) · " +
        "altitude -34.2° to +35.3° · landscape, ultra-wide lens · " +
        "obstacles above the top of the photo over 3° · GPano metadata ignored: inconsistent with the lens",
    );
  });
});
