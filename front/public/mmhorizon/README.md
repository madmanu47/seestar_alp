# MMhorizon core, compiled to WebAssembly

The Horizon page (`/horizon`) analyses a 360-degree panorama in the browser
with these two files; the photo is not uploaded.

- Source: [mmedia-fr/mmhorizon](https://github.com/mmedia-fr/mmhorizon),
  GPL-3.0-or-later, version 0.1.1, commit `afa2bae` (`wasm/` crate; branch
  `socle/tour-deux-clics`, pull request #5, which adds `fixerTour`).
- Interface: `docs/WASM.md` in that repository.
- Built with:

  ```sh
  cargo build --manifest-path wasm/Cargo.toml --release --locked --target wasm32-unknown-unknown
  wasm-bindgen --target web --out-dir dist/wasm wasm/target/wasm32-unknown-unknown/release/mmhorizon_wasm.wasm
  ```

Do not edit them: rebuild from the source, or take the `mmhorizon-noyau-wasm`
artifact of its CI, and replace both files together.

| File | SHA-256 |
|---|---|
| `mmhorizon_wasm.js` | `0effd8c0990e4d90700d677e321fd654a9b3c8e68230b8a646e6dd5d4a80e1f4` |
| `mmhorizon_wasm_bg.wasm` | `adb57c96ace3c34d7714d6b72abac2331ecfb220c7815a122e6bdca3ddc7b84b` |
