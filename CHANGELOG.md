# Changelog

## [0.7.0](https://github.com/AyakaRadiology/needle-protocol/compare/v0.6.0...v0.7.0) (2026-11-28)


### Features

* **tracker:** needle frames can carry the numbered list of needles, and the hello says which tracker run it is ([#119](https://github.com/AyakaRadiology/needle-protocol/issues/119)) ([382035e](https://github.com/AyakaRadiology/needle-protocol/commit/382035eb2570cacf5f9c6ee721c4c142261e14c5))
* **tracker:** the hello can say the tracker's positions are in the rig's frame (world), and needle frames can say the geometry is settling ([#97](https://github.com/AyakaRadiology/needle-protocol/issues/97)) ([8b1dbcc](https://github.com/AyakaRadiology/needle-protocol/commit/8b1dbccae9607351a5a4cfc0d3496b1a384394c7))


### Bug Fixes

* [agent-found] angles/ts/src/index.ts:234 When an operator checks a horizontal needle with the phantom ([#76](https://github.com/AyakaRadiology/needle-protocol/issues/76)) ([d05bf60](https://github.com/AyakaRadiology/needle-protocol/commit/d05bf6086abcc446862619e6ad7bb755897212ca)), closes [#72](https://github.com/AyakaRadiology/needle-protocol/issues/72)
* [agent-found] dist/cjs/types.d.ts:459 A CommonJS TypeScript capture replay tool validates a multi- ([#121](https://github.com/AyakaRadiology/needle-protocol/issues/121)) ([cbc7869](https://github.com/AyakaRadiology/needle-protocol/commit/cbc7869201e18b6d70e57c623c629865af4b6444)), closes [#120](https://github.com/AyakaRadiology/needle-protocol/issues/120)
* [agent-found] dist/cjs/zod-inference.d.ts:26 A CommonJS TypeScript capture validator using Zod 4 embeds t ([#114](https://github.com/AyakaRadiology/needle-protocol/issues/114)) ([3bf5081](https://github.com/AyakaRadiology/needle-protocol/commit/3bf50818fbda81d2c9391806306d4be9d89da8f6)), closes [#113](https://github.com/AyakaRadiology/needle-protocol/issues/113)
* [agent-found] dist/esm/angles.js:181 When the tracker reports a 20 mm entry-to-tip span at coordi ([#82](https://github.com/AyakaRadiology/needle-protocol/issues/82)) ([a34b022](https://github.com/AyakaRadiology/needle-protocol/commit/a34b0221dba260c34255f50c5a3a1fcbf7f61cc3)), closes [#80](https://github.com/AyakaRadiology/needle-protocol/issues/80)
* [agent-found] dist/esm/zod-inference.d.ts:13 A TypeScript capture replay tool using Zod 4 calls `TrackerH ([#111](https://github.com/AyakaRadiology/needle-protocol/issues/111)) ([dd10065](https://github.com/AyakaRadiology/needle-protocol/commit/dd10065900eefac0cce604c722cf3e99d9984380)), closes [#109](https://github.com/AyakaRadiology/needle-protocol/issues/109)
* [agent-found] dist/esm/zod.d.ts:16 A TypeScript capture validator using the supported Zod 4 pee ([#107](https://github.com/AyakaRadiology/needle-protocol/issues/107)) ([67f0636](https://github.com/AyakaRadiology/needle-protocol/commit/67f063679c28dc49fe0ddf8068b697e0a2187fca)), closes [#102](https://github.com/AyakaRadiology/needle-protocol/issues/102)
* [agent-found] dist/esm/zod.d.ts:810 An angle-stream subscriber uses the published validator on t ([#106](https://github.com/AyakaRadiology/needle-protocol/issues/106)) ([25276a2](https://github.com/AyakaRadiology/needle-protocol/commit/25276a217f312dfddc57ad0133cdfa8a0275c26f)), closes [#101](https://github.com/AyakaRadiology/needle-protocol/issues/101)
* [agent-found] gen/py/needle_protocol/models.py:31 A Python relay uses the package's Pydantic adapter to genera ([#84](https://github.com/AyakaRadiology/needle-protocol/issues/84)) ([a8f9d74](https://github.com/AyakaRadiology/needle-protocol/commit/a8f9d743c92453f575e23509b70be041e0c163a8)), closes [#83](https://github.com/AyakaRadiology/needle-protocol/issues/83)
* [agent-found] gen/py/needle_protocol/models.py:517 A Python relay receives a valid tracker hello from an older ([#103](https://github.com/AyakaRadiology/needle-protocol/issues/103)) ([5c1294f](https://github.com/AyakaRadiology/needle-protocol/commit/5c1294f5862af22be8e24a09412989de4c784d7a)), closes [#98](https://github.com/AyakaRadiology/needle-protocol/issues/98)
* [agent-found] tools/check-enum-order.py:106 A protocol maintainer intentionally reorders the released de ([#118](https://github.com/AyakaRadiology/needle-protocol/issues/118)) ([79be0ed](https://github.com/AyakaRadiology/needle-protocol/commit/79be0ed44c22c586db3a1f657797472bfb74e53d)), closes [#117](https://github.com/AyakaRadiology/needle-protocol/issues/117)
* [agent-found] tools/check-enum-order.py:41 A maintainer fetches tags while working on a branch cut from ([#78](https://github.com/AyakaRadiology/needle-protocol/issues/78)) ([7435cfc](https://github.com/AyakaRadiology/needle-protocol/commit/7435cfc564a04e9f8a1396e45a28a340f67ea1cb)), closes [#75](https://github.com/AyakaRadiology/needle-protocol/issues/75)
* [agent-found] tools/gen-py.py:278 A Python client validates and relays a tilt-only plan. The g ([#81](https://github.com/AyakaRadiology/needle-protocol/issues/81)) ([ac19ad8](https://github.com/AyakaRadiology/needle-protocol/commit/ac19ad8d963a7dc612a1356d2404f79a5ff02d3b)), closes [#79](https://github.com/AyakaRadiology/needle-protocol/issues/79)
* [agent-found] tools/gen-py.py:295 A Python plan sender passes None for an azimuth the operator ([#86](https://github.com/AyakaRadiology/needle-protocol/issues/86)) ([42f21b3](https://github.com/AyakaRadiology/needle-protocol/commit/42f21b384708a6d31a4b11cc38f9005986739d43)), closes [#85](https://github.com/AyakaRadiology/needle-protocol/issues/85)
* [agent-found] tools/gen-swift.py:435 A protocol maintainer adds a valid `maximum` constraint to ` ([#105](https://github.com/AyakaRadiology/needle-protocol/issues/105)) ([3893d76](https://github.com/AyakaRadiology/needle-protocol/commit/3893d76fb2f92b1773ca84b422e6322e208b9c57)), closes [#100](https://github.com/AyakaRadiology/needle-protocol/issues/100)
* **py:** the Python models refuse NaN and Infinity like the TypeScript and Swift bindings ([#90](https://github.com/AyakaRadiology/needle-protocol/issues/90)) ([933abfa](https://github.com/AyakaRadiology/needle-protocol/commit/933abfa51ca87a21b3b62a788ea0c57d3ffd922b))
* Python binding disagrees with schema and zod: accepts "v": true, rejects integers written as 1.0 ([#96](https://github.com/AyakaRadiology/needle-protocol/issues/96)) ([39cd726](https://github.com/AyakaRadiology/needle-protocol/commit/39cd726228be6bccd91b26ed1dbba427665dc2f6)), closes [#93](https://github.com/AyakaRadiology/needle-protocol/issues/93)
* Swift TrackerHello accepts null for server_bind, client_addr and phantom, which the schema, zod and pydantic reject ([#95](https://github.com/AyakaRadiology/needle-protocol/issues/95)) ([901d80f](https://github.com/AyakaRadiology/needle-protocol/commit/901d80f9bdb678606f5d5ba195eaa0f9749f0566)), closes [#92](https://github.com/AyakaRadiology/needle-protocol/issues/92)

## [0.6.0](https://github.com/AyakaRadiology/needle-protocol/compare/v0.5.0...v0.6.0) (2026-11-12)


### Features

* **swift:** add a root Package.swift so SwiftPM consumers can pin a tag ([#67](https://github.com/AyakaRadiology/needle-protocol/issues/67)) ([211c552](https://github.com/AyakaRadiology/needle-protocol/commit/211c5520de8c8ab5c0d2699139449febfa289750))
* **swift:** generate Swift types for the tracker schemas ([#63](https://github.com/AyakaRadiology/needle-protocol/issues/63)) ([7968ff8](https://github.com/AyakaRadiology/needle-protocol/commit/7968ff8df26b2c4ae76632fe99cd588458fe775b))
* **tracker:** hello carries the phantom id and size ([#70](https://github.com/AyakaRadiology/needle-protocol/issues/70)) ([4767713](https://github.com/AyakaRadiology/needle-protocol/commit/476771329d86f297142d9bee4648d040bc5c2b93))


### Bug Fixes

* [agent-found] dist/cjs/types.d.ts:34 A TypeScript subscriber imports AngleStreamEnvelope and pass ([#66](https://github.com/AyakaRadiology/needle-protocol/issues/66)) ([3947866](https://github.com/AyakaRadiology/needle-protocol/commit/394786635c5fe2f9b8349f7365823ca5d0cd3d8b)), closes [#64](https://github.com/AyakaRadiology/needle-protocol/issues/64)

## [0.5.0](https://github.com/AyakaRadiology/needle-protocol/compare/v0.4.3...v0.5.0) (2026-10-30)


### Features

* **tracker:** JSON Schema for the tracker needle frame and other post-hello messages ([#57](https://github.com/AyakaRadiology/needle-protocol/issues/57)) ([63f167e](https://github.com/AyakaRadiology/needle-protocol/commit/63f167e866d16be592f7615d8c0bd41e204d0558))

## [0.4.3](https://github.com/AyakaRadiology/needle-protocol/compare/v0.4.2...v0.4.3) (2026-10-22)


### Bug Fixes

* [security] high: vite 1 advisories (GHSA-587h-7wmj-h5pm) launch-editor: `fs.existsSync()` existence check can be byp… ([#48](https://github.com/AyakaRadiology/needle-protocol/issues/48)) ([1a656bd](https://github.com/AyakaRadiology/needle-protocol/commit/1a656bdfea982c8d1ae2d415ae52011e7acfc9ce)), closes [#47](https://github.com/AyakaRadiology/needle-protocol/issues/47)

## [0.4.2](https://github.com/AyakaRadiology/needle-protocol/compare/v0.4.1...v0.4.2) (2026-10-16)


### Bug Fixes

* [agent-found] dist/cjs/zod.d.ts:18 A TypeScript consumer installs Zod 4, which this package exp ([#41](https://github.com/AyakaRadiology/needle-protocol/issues/41)) ([df80c9b](https://github.com/AyakaRadiology/needle-protocol/commit/df80c9b8a578c7e3f7089575ee2e5d99f85e59f3)), closes [#38](https://github.com/AyakaRadiology/needle-protocol/issues/38)
* [agent-found] dist/esm/zod.d.ts:18 A TypeScript consumer installs the advertised Zod 4 peer ver ([#44](https://github.com/AyakaRadiology/needle-protocol/issues/44)) ([bb5aadd](https://github.com/AyakaRadiology/needle-protocol/commit/bb5aaddce4994aec45c62037244411b551243213)), closes [#39](https://github.com/AyakaRadiology/needle-protocol/issues/39)
* [agent-found] tools/gen-py.py:192 When the shared tracker constant is reduced to the single su ([#46](https://github.com/AyakaRadiology/needle-protocol/issues/46)) ([c974dc0](https://github.com/AyakaRadiology/needle-protocol/commit/c974dc0793d7fdd8af4804d41bd52bcee93e077c)), closes [#45](https://github.com/AyakaRadiology/needle-protocol/issues/45)

## [0.4.1](https://github.com/AyakaRadiology/needle-protocol/compare/v0.4.0...v0.4.1) (2026-10-08)


### Bug Fixes

* [security] high: source-map-js 1 advisories (GHSA-68fv-2mgg-jv7q) source-map-js allows event-loop denial of service through i… ([#31](https://github.com/AyakaRadiology/needle-protocol/issues/31)) ([a8a3d2e](https://github.com/AyakaRadiology/needle-protocol/commit/a8a3d2e4ce8b3a82832cb60399d1fcfc77620771)), closes [#30](https://github.com/AyakaRadiology/needle-protocol/issues/30)

## [0.4.0](https://github.com/AyakaRadiology/needle-protocol/compare/v0.3.0...v0.4.0) (2026-10-02)


### Features

* dependabot auto-merge for patch/minor updates ([#23](https://github.com/AyakaRadiology/needle-protocol/issues/23)) ([6ea806b](https://github.com/AyakaRadiology/needle-protocol/commit/6ea806bc977190b6c228707a230a7e78bc66ade9))

## [0.3.0](https://github.com/AyakaRadiology/needle-protocol/compare/v0.2.0...v0.3.0) (2026-09-05)


### Features

* **plan-channel:** entry_longitudinal_mm accepts ±3000 mm (CT table travel) ([#17](https://github.com/AyakaRadiology/needle-protocol/issues/17)) ([6b62f29](https://github.com/AyakaRadiology/needle-protocol/commit/6b62f29c869c5157d572a5400ebe8255d87055c7))

## [0.2.0](https://github.com/AyakaRadiology/needle-protocol/compare/v0.1.0...v0.2.0) (2026-09-04)


### Features

* **plan-channel:** Simulator → Guide plan contract (req/res, strict, revisioned) ([#15](https://github.com/AyakaRadiology/needle-protocol/issues/15)) ([d6ebfc2](https://github.com/AyakaRadiology/needle-protocol/commit/d6ebfc29240fa9bb42cf0677fd3f3acf9b35c3f7))

## 0.1.0 (2026-09-04)


### Features

* **pkg:** export angles/vectors.json for consumers ([#11](https://github.com/AyakaRadiology/needle-protocol/issues/11)) ([f887afe](https://github.com/AyakaRadiology/needle-protocol/commit/f887afea5d8c643dc2a994d7aa68745bec14cc3a))
* **schemas:** status payload carries envelope_schema_version once per session ([#2](https://github.com/AyakaRadiology/needle-protocol/issues/2)) ([262a35a](https://github.com/AyakaRadiology/needle-protocol/commit/262a35a524b3f5cfbb72168556da675ca8732a1d))
* shared wire contracts, angle conventions and constants ([19e9de9](https://github.com/AyakaRadiology/needle-protocol/commit/19e9de986722084f3cd933acc1d2074ed1a470a0))
