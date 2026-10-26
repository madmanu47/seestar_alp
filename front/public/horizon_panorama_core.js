// Horizon page: helpers without DOM or WebAssembly, shared by the page and its
// worker (and tested in front/tests/horizon_panorama.test.js).

/*
 * Horizon line (row at altitude 0) once the Sun, seen at row sunRow, is known
 * to stand at sunAltitude. rowOfSunAltitude is the row of that altitude under
 * the current horizon line: both projections MMhorizon handles move every
 * altitude by the same number of rows when the horizon line moves.
 */
export function horizonLineFromSun(sunRow, rowOfSunAltitude, currentHorizon) {
  return sunRow + (currentHorizon - rowOfSunAltitude);
}

/*
 * Photo date (EXIF, ISO 8601) as a UTC ISO string for /horizon/sun. A date
 * without UTC offset is read as this browser's local time.
 */
export function photoTimeUtc(exifDate) {
  if (!exifDate) {
    return null;
  }
  const date = new Date(exifDate);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

export function hasUtcOffset(exifDate) {
  return /([+-]\d\d:?\d\d|Z)$/.test(exifDate || "");
}

/*
 * Position in the photo, in pixels, of a pointer event on a canvas that shows
 * the photo scaled to canvasWidth x canvasHeight and is drawn in rect.
 */
export function photoPoint(clientX, clientY, rect, canvasWidth, canvasHeight, photoWidth, photoHeight) {
  const x = ((clientX - rect.left) / rect.width) * canvasWidth;
  const y = ((clientY - rect.top) / rect.height) * canvasHeight;
  return {
    column: (x * photoWidth) / canvasWidth,
    row: (y * photoHeight) / canvasHeight,
  };
}

/*
 * SVG points of a profile of 360 altitudes (null where the panorama gave
 * none), for a viewBox where x is the azimuth and y = 90 - altitude, clamped
 * to 0-90 degrees as on the Planning page's Horizon card.
 */
export function profilePoints(altitudes) {
  const points = ["0,90"];
  altitudes.forEach((altitude, azimuth) => {
    const value = Math.min(Math.max(altitude ?? 0, 0), 90);
    points.push(`${azimuth},${round(90 - value, 2)}`);
  });
  const first = Math.min(Math.max(altitudes[0] ?? 0, 0), 90);
  points.push(`360,${round(90 - first, 2)}`, "360,90");
  return points.join(" ");
}

const WORDS = {
  cylindrique: "cylindrical",
  equirectangulaire: "equirectangular",
  gpano: "GPano metadata",
  chevauchement: "overlap",
  supposee: "assumed full turn",
  paysage: "landscape",
  portrait: "portrait",
  inconnue: "unknown",
  inconnu: "unknown",
  principal: "main lens",
  "ultra-grand-angle": "ultra-wide lens",
  teleobjectif: "telephoto lens",
};

function word(value) {
  return WORDS[value] ?? value;
}

/* One-line summary of an MMhorizon infos() object. */
export function summary(infos) {
  const [low, high] = infos.champ_vertical_deg;
  const parts = [
    `${infos.largeur} × ${infos.hauteur} px`,
    word(infos.projection),
    `${Math.round(infos.couverture_deg)}° of azimuth (${word(infos.couverture_methode)})`,
    `altitude ${signed(low)}° to ${signed(high)}°`,
    `${word(infos.orientation)}, ${word(infos.objectif)}`,
  ];
  if (infos.au_dela_du_champ > 0) {
    parts.push(`obstacles above the top of the photo over ${infos.au_dela_du_champ}°`);
  }
  if (infos.gpano_ecarte) {
    parts.push("GPano metadata ignored: inconsistent with the lens");
  }
  return parts.join(" · ");
}

function signed(value) {
  const text = round(value, 1).toFixed(1);
  return value >= 0 ? `+${text}` : text;
}

function round(value, decimals) {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}
