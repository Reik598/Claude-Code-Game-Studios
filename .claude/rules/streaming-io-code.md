---
paths:
  - "engine/streaming/**"
  - "engine/assets/**"
  - "engine/io/**"
  - "engine/media/**"
  - "crates/streaming/**"
  - "crates/assets/**"
  - "crates/io/**"
  - "crates/media/**"
---

# Streaming, Asset and I/O Code Rules

For a project that builds its own engine (`engine.name: Custom`). Runtime
streaming and asset loading are owned by `world-streaming-engineer`; the OS
file layer by `platform-engineer` (both report to `core-systems-lead`); the
cooked formats' writers by `asset-build-tooling-engineer`. Video and media
playback in `engine/media/` is owned by `platform-engineer` (platform codecs)
with `audio-engine-engineer` for audio sync; media files are streamed and
decoded off the game and render threads under the same rules as any asset.
On any other engine, ignore this file.

## Asynchronous only

- Every read goes through the engine's asynchronous request API and returns a
  handle. The backend (a thread pool, io_uring, DirectStorage, a platform API)
  is an ADR choice hidden behind `engine/io/`
- The game thread and the render thread never read a file synchronously and
  never wait on a request inside a frame: no `fread`, `std::ifstream`,
  `std::fs::read`, or `request.wait()` on those threads. They poll for
  completion or receive a callback on a known thread
- Every request can be cancelled. A cancelled request returns its buffer to its
  pool and never calls its completion
- Every request carries a priority (for example: needed this frame, visible
  soon, prefetch), and streaming re-prioritises as the camera moves. The classes
  and their order are recorded in an ADR
- Load-time targets come from config and are measured from the request to
  usable data, not to the end of the read

## Memory budget

- Streaming pools have fixed budgets from config. A pool at its budget evicts
  by priority and then least recently used; it never grows into the general heap
- In-flight memory (read buffers, decompression scratch) is counted against a
  budget too, and a request that cannot fit waits in the queue, not in a frame

## Asset formats are untrusted input

Files on disk may be corrupted, truncated, out of date, modded or tampered with.

- Every format starts with a magic number, a format version and the payload
  size. An unknown version is a reported error, never a crash or a guess
- The loader validates every count, offset and size against the buffer length
  before using it, with overflow-checked arithmetic. No pointer is formed from
  an unchecked offset
- Every chunk carries a checksum (the algorithm is an ADR choice) verified
  before it is decompressed or decoded; decompression writes into a buffer of
  the size the header declared, bounded, and fails if the output would exceed it
- Load failures are values (`std::expected`, `Result`), handled by falling back
  to a placeholder asset and reporting, never by `abort` or `unwrap`
- A format change bumps the version and either keeps a reader for the old one
  or forces a re-cook; `asset-build-tooling-engineer` changes the writer in the
  same change

## Mod and downloaded packages are untrusted

- Mod packages and downloaded content are mounted read-only through the same
  I/O layer, each at a mount point of its own. A mod overrides an asset only
  through the override list in its manifest, applied in the resolved load
  order, and the resulting override set is logged
- Paths inside a package are relative, normalised and checked against the
  package root before use. OWASP's path traversal description is the threat:
  dot-dot-slash sequences or absolute paths that reach files outside the
  intended root
- Size limits apply after decompression as well as before. OWASP lists ZIP
  bombs among the attacks on uploaded files and says the size limit should be
  considered after decompression
- A package is validated in full (manifest, format versions, checksums) before
  it is mounted; one that fails is refused with the reason, never mounted in
  part

## Examples

**Correct** — C++23:

```cpp
std::expected<mesh_view, load_error> parse_mesh(std::span<const std::byte> bytes)
{
    auto hdr = read_header(bytes);                         // checks magic and length
    if (!hdr) return std::unexpected(hdr.error());
    if (hdr->version != mesh_format_version) return std::unexpected(load_error::version);
    if (!fits(bytes, hdr->payload_offset, hdr->payload_size, 1))
        return std::unexpected(load_error::out_of_bounds); // overflow-checked, before any subspan
    auto payload = bytes.subspan(hdr->payload_offset, hdr->payload_size);
    if (checksum(payload) != hdr->checksum)                // checksum the validated range only
        return std::unexpected(load_error::checksum);
    if (!fits(payload, hdr->vertex_offset, hdr->vertex_count, sizeof(vertex)))
        return std::unexpected(load_error::out_of_bounds);
    return mesh_view{*hdr, payload};
}

auto req = io.request({.path = cell.path, .priority = priority::visible_soon, .pool = &cell_pool});
```

Rust:

```rust
pub fn parse_mesh(bytes: &[u8]) -> Result<MeshView<'_>, LoadError> {
    let hdr = Header::read(bytes)?; // checks magic and length
    if hdr.version != MESH_FORMAT_VERSION { return Err(LoadError::Version(hdr.version)); }
    let payload_end = hdr.payload_offset.checked_add(hdr.payload_size).ok_or(LoadError::OutOfBounds)?;
    let payload = bytes.get(hdr.payload_offset..payload_end).ok_or(LoadError::OutOfBounds)?;
    if checksum(payload) != hdr.checksum { return Err(LoadError::Checksum); } // the validated range only
    let end = hdr.vertex_count.checked_mul(size_of::<Vertex>())
        .and_then(|n| n.checked_add(hdr.vertex_offset)).ok_or(LoadError::OutOfBounds)?;
    let vertices = payload.get(hdr.vertex_offset..end).ok_or(LoadError::OutOfBounds)?;
    Ok(MeshView { hdr, vertices })
}
```

**Incorrect**:

```cpp
void level::on_enter_cell(cell_id id)                     // game thread
{
    std::ifstream f(path_for(id), std::ios::binary);     // VIOLATION: synchronous read in a frame
    auto* hdr = reinterpret_cast<const header*>(buf.data());
    auto* verts = reinterpret_cast<const vertex*>(buf.data() + hdr->vertex_offset); // VIOLATION: unchecked offset
}
```

```rust
let bytes = std::fs::read(path).unwrap();        // VIOLATION: blocking read, panics on error
let hdr: &Header = unsafe { &*(bytes.as_ptr() as *const Header) }; // VIOLATION: no size, alignment or version check
```
