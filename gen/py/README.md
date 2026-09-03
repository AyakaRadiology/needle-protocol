# needle-protocol (Python)

Generated distribution of the shared wire contracts. **Do not edit anything in
this directory**: it is produced by `tools/gen.sh` from `schemas/`,
`constants/constants.json` and `angles/py/`, and CI fails on any drift.

Install from a tag:

```
needle-protocol @ git+https://github.com/AyakaRadiology/needle-protocol@v0.1.0#subdirectory=gen/py
```

`needle_protocol.constants` and `needle_protocol.angles` are standard library
only. `needle_protocol.models` needs the `models` extra (pydantic v2).
