/*
 * Compile-and-run check for the generated firmware header.
 *
 * The Pico consumes gen/c/schema_keys.h through a CMake custom command, and a
 * header that does not compile there fails a build nobody in this repository
 * runs. So it is compiled here, warnings-as-errors, and the assertions below
 * pin the two properties the firmware actually depends on:
 *
 *   1. every KEY_* macro the firmware references still exists, and
 *   2. each enum constant's integer value is still its index in the schema's
 *      enum array -- the property tools/check-enum-order.py guards across
 *      releases, asserted here within one.
 *
 * Built by tests/c/run.sh, which also compiles the header as C++ because the
 * firmware is C++ and the header's `__cplusplus` branch is otherwise dead code
 * that nothing would ever tell us had broken.
 */
#include <stdio.h>
#include <string.h>

#include "schema_keys.h"

static int failures = 0;

#define CHECK(cond)                                                         \
    do {                                                                    \
        if (!(cond)) {                                                      \
            printf("  FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);        \
            failures++;                                                     \
        }                                                                   \
    } while (0)

int main(void) {
    /* Envelope keys, as docs/PROTOCOL.md spells them. */
    CHECK(strcmp(KEY_V, "v") == 0);
    CHECK(strcmp(KEY_KIND, "kind") == 0);
    CHECK(strcmp(KEY_TYPE, "type") == 0);
    CHECK(strcmp(KEY_SEQ, "seq") == 0);
    CHECK(strcmp(KEY_PAYLOAD, "payload") == 0);

    /* The renamed clock. `ts` read as wall-clock time is wrong by however long
     * the device has been powered, which is why the key says which clock it is. */
    CHECK(strcmp(KEY_T_BOOT_MS, "t_boot_ms") == 0);

    /* Payload keys. */
    CHECK(strcmp(KEY_ACCEL_X, "accel_x") == 0);
    CHECK(strcmp(KEY_ACCEL_Y, "accel_y") == 0);
    CHECK(strcmp(KEY_ACCEL_Z, "accel_z") == 0);
    CHECK(strcmp(KEY_STATE, "state") == 0);
    CHECK(strcmp(KEY_CODE, "code") == 0);
    CHECK(strcmp(KEY_MESSAGE, "message") == 0);
    CHECK(strcmp(KEY_LEVEL, "level") == 0);

    /* Enum value == index in the schema's array. A device stores these
     * integers, so a reordered array renumbers state a flashed Pico already
     * holds -- see tools/check-enum-order.py. */
    CHECK(STATE_INIT == 0);
    CHECK(STATE_READY == 1);
    CHECK(STATE_LOST == 4);
    CHECK(strcmp(state_t_to_cstr[STATE_DEGRADED], "degraded") == 0);
    CHECK(state_t_from_cstr("stopped") == STATE_STOPPED);
    CHECK(state_t_from_cstr("no-such-state") == -1);
    CHECK(state_t_from_cstr(NULL) == -1);

    CHECK(TYPE_STATUS == 0);
    CHECK(strcmp(type_t_to_cstr[TYPE_DATA], "data") == 0);
    CHECK(type_t_from_cstr("log") == TYPE_LOG);

    CHECK(LEVEL_TRACE == 0);
    CHECK(strcmp(level_t_to_cstr[LEVEL_CRITICAL], "critical") == 0);
    CHECK(level_t_from_cstr("info") == LEVEL_INFO);

    /* The compatibility numbers the firmware reports, straight out of the
     * schemas rather than out of a hand-kept literal beside them. */
    CHECK(strcmp(SCHEMA_DEVICE_ENVELOPE_XVERSION, "2.0.0") == 0);
    CHECK(strcmp(SCHEMA_DEVICE_PAYLOAD_DATA_XVERSION, "1.0.0") == 0);
    CHECK(strcmp(SCHEMA_DEVICE_PAYLOAD_STATUS_XVERSION, "1.0.0") == 0);
    CHECK(strcmp(SCHEMA_DEVICE_PAYLOAD_ERROR_XVERSION, "1.0.0") == 0);
    CHECK(strcmp(SCHEMA_DEVICE_PAYLOAD_LOG_XVERSION, "1.0.0") == 0);

    if (failures != 0) {
        printf("schema_keys.h: %d check(s) failed\n", failures);
        return 1;
    }
    printf("schema_keys.h: all checks passed\n");
    return 0;
}
