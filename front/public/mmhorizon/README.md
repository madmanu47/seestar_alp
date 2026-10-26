# MMhorizon core, compiled to WebAssembly

The Horizon page (`/horizon`) analyses a 360-degree panorama in the browser
with these two files; the photo is not uploaded.

- Source: [mmedia-fr/mmhorizon](https://github.com/mmedia-fr/mmhorizon),
  GPL-3.0-or-later, release
  [v0.1.2](https://github.com/mmedia-fr/mmhorizon/releases/tag/v0.1.2), commit
  `5f5f18f` (`wasm/` crate): the two files of `mmhorizon-noyau-wasm-0.1.2.zip`.
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
| `mmhorizon_wasm_bg.wasm` | `090210371cd73da7e21f4cb3262c3e6818e6f3ce4bd3be78196cea0bbf25579e` |
