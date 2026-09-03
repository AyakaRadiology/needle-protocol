/*
 * AUTO-GENERATED FILE. DO NOT EDIT.
 * Source schemas: 5 file(s)
 */
#ifndef SCHEMA_KEYS_H_
#define SCHEMA_KEYS_H_

/* ---- Schema x-version (device<->host compatibility, per SECURITY.md) ----
 * These are the numbers that decide whether a host can read this device, and
 * they move INDEPENDENTLY of the envelope's `v` and of the package version.
 * Emitted so the firmware can report the contract it was built against rather
 * than a hand-kept literal that drifts from the schema beside it.
 */
#define SCHEMA_DEVICE_ENVELOPE_XVERSION "2.0.0"
#define SCHEMA_DEVICE_PAYLOAD_DATA_XVERSION "1.0.0"
#define SCHEMA_DEVICE_PAYLOAD_ERROR_XVERSION "1.0.0"
#define SCHEMA_DEVICE_PAYLOAD_LOG_XVERSION "1.0.0"
#define SCHEMA_DEVICE_PAYLOAD_STATUS_XVERSION "1.0.0"

/* ---- Key name string macros ---- */
#define KEY_ACCEL_X "accel_x"
#define KEY_ACCEL_Y "accel_y"
#define KEY_ACCEL_Z "accel_z"
#define KEY_CODE "code"
#define KEY_DETAIL "detail"
#define KEY_KIND "kind"
#define KEY_LEVEL "level"
#define KEY_MESSAGE "message"
#define KEY_PAYLOAD "payload"
#define KEY_SEQ "seq"
#define KEY_STATE "state"
#define KEY_T_BOOT_MS "t_boot_ms"
#define KEY_TYPE "type"
#define KEY_V "v"

/* ---- C++ friendly string_view (optional) ---- */
#ifdef __cplusplus
#include <string_view>
namespace schema_keys {
inline constexpr std::string_view accel_x = "accel_x";
inline constexpr std::string_view accel_y = "accel_y";
inline constexpr std::string_view accel_z = "accel_z";
inline constexpr std::string_view code = "code";
inline constexpr std::string_view detail = "detail";
inline constexpr std::string_view kind = "kind";
inline constexpr std::string_view level = "level";
inline constexpr std::string_view message = "message";
inline constexpr std::string_view payload = "payload";
inline constexpr std::string_view seq = "seq";
inline constexpr std::string_view state = "state";
inline constexpr std::string_view t_boot_ms = "t_boot_ms";
inline constexpr std::string_view type = "type";
inline constexpr std::string_view v = "v";
} // namespace schema_keys
extern "C" {
#endif

/* ---- Enums derived from schema enums ---- */
typedef enum level_t {
  LEVEL_TRACE = 0,
  LEVEL_DEBUG = 1,
  LEVEL_INFO = 2,
  LEVEL_WARN = 3,
  LEVEL_ERROR = 4,
  LEVEL_CRITICAL = 5
} level_t;

typedef enum state_t {
  STATE_INIT = 0,
  STATE_READY = 1,
  STATE_RUNNING = 2,
  STATE_DEGRADED = 3,
  STATE_LOST = 4,
  STATE_STOPPING = 5,
  STATE_STOPPED = 6
} state_t;

typedef enum type_t {
  TYPE_STATUS = 0,
  TYPE_DATA = 1,
  TYPE_ERROR = 2,
  TYPE_LOG = 3
} type_t;


/* ---- Lookup helpers (header-only, internal linkage) ---- */
/* Header-only helpers with internal linkage */
#include <stddef.h>
#include <string.h>
static const char* level_t_to_cstr[6] = {
  "trace",
  "debug",
  "info",
  "warn",
  "error",
  "critical"
};

static const char* state_t_to_cstr[7] = {
  "init",
  "ready",
  "running",
  "degraded",
  "lost",
  "stopping",
  "stopped"
};

static const char* type_t_to_cstr[4] = {
  "status",
  "data",
  "error",
  "log"
};


static inline int level_t_from_cstr(const char* s) {
  if (!s) return -1;
  for (int i = 0; i < 6; ++i) {
    if (strcmp(s, level_t_to_cstr[i]) == 0) return i;
  }
  return -1;
}

static inline int state_t_from_cstr(const char* s) {
  if (!s) return -1;
  for (int i = 0; i < 7; ++i) {
    if (strcmp(s, state_t_to_cstr[i]) == 0) return i;
  }
  return -1;
}

static inline int type_t_from_cstr(const char* s) {
  if (!s) return -1;
  for (int i = 0; i < 4; ++i) {
    if (strcmp(s, type_t_to_cstr[i]) == 0) return i;
  }
  return -1;
}



#ifdef __cplusplus
} // extern "C"
#endif
#endif /* SCHEMA_KEYS_H_ */
