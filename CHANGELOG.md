# Changelog

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
