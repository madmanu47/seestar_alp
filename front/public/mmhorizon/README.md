# MMhorizon core, compiled to WebAssembly

The Horizon page (`/horizon`) analyses a 360-degree panorama in the browser
with these two files; the photo is not uploaded.

- Source: [mmedia-fr/mmhorizon](https://github.com/mmedia-fr/mmhorizon),
  GPL-3.0-or-later, version 0.1.1, commit `fa75ece` (`wasm/` crate).
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
| `mmhorizon_wasm.js` | `11ed58ec7f0af8bfb3f068c3a3323b2b92b54f65390aaf552bd0f0d279278454` |
| `mmhorizon_wasm_bg.wasm` | `40594021e0dcfc932b95814a759176bd400abc7bec87aaade08eee9c48c194fe` |
