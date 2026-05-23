<div align="center">

<h1>Versioning Policy</h1>

<p>
    <a href="README.md"><b>README</b></a> ·
    <b>Versioning</b> ·
    <a href="CHANGELOG.md"><b>Changelog</b></a>
  </p>

</div>

---

This document is the authoritative policy for how The Way Out is
versioned, released, supported, and retired. It is the contract every
release of the game honours; a breach of any clause stated with
**MUST** is a bug, not a feature.

The Way Out is a shipping game with a save file and an in-game updater.
Versioning a game is not the same as versioning a library: the contract
that matters most to a player is "**my save still loads**", not "the
function signature did not change". This policy is written around that.

Companion documents:

- [`README.md`](README.md) — what the game is, how to install and play.
- [`CHANGELOG.md`](CHANGELOG.md) — the per-release human-readable log.
- [`VERSION`](VERSION) — the canonical version string the in-game
  updater reads. **This file is the single source of truth** for the
  running version (see §3).

The keywords **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and
**MAY** in this document are to be interpreted as described in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## 1. Scope

This policy governs every artefact released under the
[`ajhahnde/the-way-out`](https://github.com/ajhahnde/the-way-out) GitHub
repository: the source tree, the GitHub Release archives, and the
in-game updater endpoint that serves them. It applies from **v1.0.0**
(2026-05-21) onward.

## 2. Grammar

The Way Out follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)
adapted for a game, with **save-file compatibility** as the primary
breaking-change axis.

A release version is `vMAJOR.MINOR.PATCH` (the leading `v` is preserved
on every git tag, GitHub Release, and CHANGELOG section header)
optionally followed by a pre-release identifier as defined in §7.

| Component | Trigger |
|---|---|
| **MAJOR** | A breaking change to the save-file format that cannot be forward-migrated; a breaking change to the in-game updater protocol; a breaking change to the asset-pack format once it becomes part of the public surface (§3.2). |
| **MINOR** | New content — a new level, character, weapon, mechanic, or scripted event. Saves from any previous MINOR within the same MAJOR MUST remain loadable (with forward migration if needed, see §4). |
| **PATCH** | A bug fix, balance tweak, performance improvement, art correction, or text fix. PATCH MUST NOT touch the save-file schema and MUST NOT touch the in-game updater protocol. A save from any previous PATCH within the same MINOR MUST load byte-identically. |

A change that fits more than one bucket MUST take the most disruptive
applicable bucket (e.g., a bug fix that requires a save-schema bump
ships as the next MINOR or MAJOR depending on whether forward migration
is possible — never as a PATCH).

## 3. Public surface

The **frozen public surface** of The Way Out is the union of:

### 3.1 Save-file format

The on-disk layout of a save file: every field name, type, and
permitted value, the schema version embedded in the save header, and
the rules for forward migration described in §4.

A new optional field MAY be added in a MINOR (it appears as missing in
old saves and is given a documented default on load). A field MAY NOT
be removed, renamed, or have its type changed except across a MAJOR
that ships a forward migration; if forward migration is technically
impossible (§4.3), the MAJOR release MUST document that the save line
is broken and the migration path is "start a new game".

### 3.2 In-game updater protocol

The HTTP endpoint shape the in-game launcher polls, the JSON response
schema, the artefact-naming convention used to construct the download
URL, and the SHA256 verification rules the launcher applies to the
downloaded archive before installing it.

A new optional response field MAY be added in a MINOR. The endpoint
URL itself, the required response fields, the artefact-naming
convention, and the verification rules MUST NOT change except across a
MAJOR. A MAJOR that breaks updater protocol compatibility MUST be
preceded by the §6 announcement window because a player on an older
binary cannot in-place upgrade across the break.

### 3.3 `VERSION` file

The repository contains a `VERSION` file at the root whose single line
is the canonical version string the in-game launcher reads at runtime
and that the updater protocol exposes. The file MUST:

- Contain exactly one line.
- Match `^v[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$`.
- Be updated **in the same commit** as the git tag for the release. A
  tag-without-bump or a bump-without-tag is a release-process bug.

The version exposed by `pyproject.toml` and any in-app About screen
MUST match the `VERSION` file string. A drift between any two of them
is a release-process bug. (The `eeco` `version-sync` workflow is the
recommended way to enforce this in CI; see [`eeco`'s docs](https://github.com/ajhahnde/eeco/blob/main/docs/USAGE.md).)

### 3.4 What is NOT part of the public surface

The following MAY change in any release without a MAJOR bump:

- The Python package layout under the source tree.
- Asset filenames inside `the-way-out.app/Contents/Resources/` and
  the build-tooling under `scripts/` and the `build_mac_*.sh` glue.
- Mod / asset-pack format. The game does not currently ship a mod
  surface. If and when one ships, it enters this policy as a §3.2-
  shaped clause in the MAJOR that introduces it.
- Internal class names, function signatures, the choice of game-loop
  driver, or the rendering pipeline.
- The presentation of the in-game UI — fonts, palette, spacing,
  cursor shape, dialogue framing. None of these are visible from a
  save file or from the updater protocol.

## 4. Save-file migration

The Way Out makes three promises about save-file handling and one
explicit non-promise.

### 4.1 Forward migration (promised)

A PATCH or MINOR MUST load every save written by any previous PATCH
or MINOR within the same MAJOR. When the in-memory representation has
changed, the migration MUST be transparent (the player sees no prompt)
and MUST be applied on the first re-save — old fields are read, the
new representation is computed, and the next write produces a save in
the new schema.

### 4.2 Backward migration (not promised)

A save written by a newer version is **not** guaranteed to load on an
older binary. Downgrading the game after a save has been written by a
newer version MAY render the save unreadable. The game MUST NOT
attempt to "downgrade" a save in place.

### 4.3 MAJOR migration (best-effort)

A MAJOR release SHOULD ship a forward-migration path for the previous
MAJOR's saves and SHOULD attempt the migration on load. When the
schema change makes a clean migration technically impossible:

- The MAJOR release MUST detect the older-schema save on load and
  refuse to corrupt it (the save is left on disk, untouched).
- The launcher MUST display a banner on first run after the upgrade
  explaining that an older save was detected and naming the previous
  MAJOR's last release as the version that can still load it.
- The CHANGELOG entry for the MAJOR MUST carry a `### Save migration`
  subsection that documents what the player can and cannot carry
  across.

### 4.4 Save integrity

The save file MUST carry an embedded schema version. The loader MUST
refuse to interpret a save whose schema version is unknown to the
running binary, with a player-visible message naming the schema
version found and the version the running binary supports. Silent
truncation, silent default-substitution for unknown fields, or
attempting to "fix up" an unrecognised save is **forbidden**.

## 5. Release cadence

| Bump | Target cadence | Hard rule |
|---|---|---|
| **PATCH** | As-ready. A crash-on-launch or save-corrupting bug SHOULD reach a tagged PATCH within **72 hours** of confirmation. | Never blocked on a feature. |
| **MINOR** | As-ready (no train). A MINOR ships when a content slice is complete and balanced. | Each MINOR MUST be additive over the previous MINOR within the same MAJOR (§2). |
| **MAJOR** | As-needed. A MAJOR MUST be announced under `## [Unreleased]` in [`CHANGELOG.md`](CHANGELOG.md) **at least 30 days** before its tag. The announcement enumerates every save-format and updater-protocol change. | An RC train (§7) MUST precede the GA tag of any MAJOR. |

## 6. Branching and tagging

- The default branch is `main`. Every release tag is reachable from
  `main` at the moment of tagging.
- Only **one** Stream is supported (§8). No `stable-X.Y` branches.
- A release tag MUST match the regex `^v[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$`.
- A release tag MUST NOT be deleted, force-moved, or re-pointed. A
  defective release is handled by the yank procedure (§10).

## 7. Pre-releases

A pre-release tag carries the suffix `-rc.N` (release candidate; `N`
is a strictly increasing non-negative integer starting at `0`).
`-alpha` and `-beta` pre-release identifiers are **not** used at the
present time.

- An RC MUST be used for every MAJOR. It SHOULD be used for any MINOR
  whose save-format change requires a non-trivial forward migration
  (§4.1).
- An RC MUST be published to GitHub Releases marked as **pre-release**
  and MUST NOT be exposed by the in-game updater protocol (§3.2) as
  the latest stable.
- The RC train ends when the corresponding GA tag is cut from the same
  commit as the last RC, with no behaviour change between the two.

A future mod-tooling preview channel — if one is ever needed — would
introduce a `-beta.N` track separate from `-rc.N`. The introduction of
that channel is itself a MINOR.

## 8. Support windows

The Way Out supports **one** stream: the latest stable release.

| Tier | Receives | Applies to | Ends |
|---|---|---|---|
| **Latest Stable** | Every bug fix, balance tweak, content addition, and security fix. Save migration is forward only (§4). | The most recent tag with no `-rc.N` suffix. | When the next non-pre-release tag ships. |
| **Archived** | Nothing. | Every release older than the current Latest Stable. | Permanent. |

There is no Maintenance tier and no LTS. The intent is honesty: this
is an indie game maintained by a single operator and a multi-track
support model would not be sustainable. A player who needs the latest
fix MUST upgrade — the in-game updater is the supported path; a
manual replacement of the `.app` is the fallback.

A defect that cannot be fixed in a forward-only PATCH (e.g., a defect
that requires a save-schema change to repair) is handled by the
yanked-PATCH + follow-up-MINOR pattern of §10, not by a backport.

## 9. Deprecation policy

A frozen-surface item may be removed only via a MAJOR. The procedure:

### 9.1 Announce

- A `### Deprecated` section is added to the next release's CHANGELOG
  entry, naming each deprecated item, the replacement (if any), and
  the earliest version in which the item MAY be removed.
- When the item has a runtime presence — a game mechanic, a save
  field, an updater-protocol response field — the next release after
  the announcement SHOULD ship a compatibility shim: the field is
  still accepted on load and re-written on save, but the mechanic
  itself MAY be a no-op.

### 9.2 Wait

The minimum window between the deprecation MINOR and the removal MAJOR
MUST be:

- One **MINOR release** carrying the compatibility shim, **and**
- At least **3 months** of wall-clock time.

The shorter window relative to library-style projects reflects that
The Way Out is opinionated game content: leaving a removed mechanic
half-attached for 6+ months hurts the game more than it helps any
player.

### 9.3 Remove

- Removal MUST happen in a MAJOR. A PATCH or MINOR MUST NOT remove a
  deprecated frozen-surface item.
- The MAJOR that removes the item MUST list it in the `### Removed`
  CHANGELOG section together with the save-migration note (§4.3).

## 10. Yank and recall

A release MAY be yanked only for one of:

- A save-corruption defect.
- A crash on launch under a published support configuration (the
  macOS versions named in [`README.md`](README.md) at release time).
- A signing or distribution-channel defect that prevents trusted
  install.

The yank procedure:

1. The GitHub Release for the yanked tag is edited: title is prefixed
   `[YANKED]`, body opens with one paragraph naming the yank reason and
   the recommended replacement version. The release is marked
   pre-release so it is no longer the latest.
2. The in-game updater MUST be reverted to point at the previous
   stable release within 24 hours of the yank (an updater-side
   response is the supported channel; in the absence of an updater
   change, the launcher discovers the yank from the GitHub Release
   metadata on the next poll and refuses to install the yanked tag).
3. The CHANGELOG entry for the yanked release is amended (in a follow-
   up commit on `main`) to prepend a `**YANKED on YYYY-MM-DD**` notice.
4. The fix is shipped as a follow-up PATCH within 72 hours of the yank,
   or — if a PATCH is technically insufficient — as the next MINOR
   under an accelerated cadence.
5. The yanked tag is **never** deleted or force-moved. It remains for
   audit and for players who installed it before the yank.

## 11. Security release policy

The Way Out is an offline single-player game. Its only network
interaction is the in-game updater poll. The security surface is:

- The integrity of the artefact the updater downloads — protected by
  the SHA256 verification the launcher applies before extracting the
  archive (§3.2).
- The integrity of the updater endpoint itself — TLS-only; a plaintext
  HTTP response from the endpoint MUST be ignored by the launcher.
- No user data leaves the device. The updater poll carries the running
  version string and nothing else.

A defect in any of the above is a security report. The reporting
channel is the GitHub Private Vulnerability Reporting flow on this
repository. The default embargo window between report and tagged fix
is **90 days**, in line with Project Zero industry practice. A fix
MUST be issued as a PATCH on Latest Stable (§8); there is no
maintenance line to backport to.

## 12. Roadmap signalling

A breaking change MUST NOT be a surprise to a player.

- Every save-format or updater-protocol change planned for the next
  MAJOR MUST be listed under `## [Unreleased]` in [`CHANGELOG.md`](CHANGELOG.md)
  **before** the first RC of that MAJOR.
- The list is updated whenever a candidate breaking change is added or
  removed; the diff itself is the public signal.
- The §5 ≥30-day announcement window starts from the date the
  `[Unreleased]` block first contains the final list, not from when
  the RC ships.

## 13. Governance

The Way Out is maintained by a single operator. A release MUST be
cut by:

1. A commit on `main`.
2. Bumping the `VERSION` file (§3.3) and the version field in
   `pyproject.toml` in the same commit.
3. Adding the release section to [`CHANGELOG.md`](CHANGELOG.md).
4. Building the macOS `.app` from a clean tree, verifying that an
   existing save from the previous PATCH and a save from the previous
   MINOR both load (§4.1), and that the launcher's update check
   reports the new version correctly.
5. Tagging the commit `vX.Y.Z[-rc.N]` and pushing the tag; uploading
   the `.app` archive(s) to the GitHub Release; verifying that the
   in-game updater sees the new version within 1 hour of the upload.

This policy MAY be amended; an amendment MUST itself follow the
versioning of this repository — a substantive change to the contract
is announced under `## [Unreleased]` and lands together with the next
release. A clarifying edit (typo, link rot, formatting) MAY land at
any time.

---

[← Prev: README](README.md) · [Next: Changelog →](CHANGELOG.md)
