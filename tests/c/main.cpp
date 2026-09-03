/*
 * The header's C++ face, which is the one the firmware actually uses.
 *
 * `schema_keys.h` has a `__cplusplus` branch exposing every key as a
 * `constexpr std::string_view` and wrapping the rest in `extern "C"`. Nothing
 * else in this repository compiles C++, so without this file that branch is
 * dead code and a break in it would surface as a firmware build failure in
 * another repository, days later.
 */
#include <cstdio>
#include <string_view>

#include "schema_keys.h"

int main() {
    static_assert(schema_keys::t_boot_ms == std::string_view{"t_boot_ms"});
    static_assert(schema_keys::accel_z == std::string_view{"accel_z"});
    static_assert(schema_keys::payload == std::string_view{"payload"});
    static_assert(STATE_READY == 1);
    static_assert(TYPE_DATA == 1);
    std::printf("schema_keys.h: C++ face compiles (envelope x-version %s)\n",
                SCHEMA_DEVICE_ENVELOPE_XVERSION);
    return 0;
}
