// The airwindows models compiled into one plugin: a generated table (tools/gen_categories.py) of names and factories.
#pragma once
#include "airwin_consolidated_base.h"

struct aw_model_t {
    const char *name;
    int (*num_params)();
    AirwinConsolidatedBase *(*create)();
};
extern const aw_model_t AW_MODELS[];
extern const int AW_NUM_MODELS;
// per model: the control-slot map (slot -> effect parameter, -1 unused) and its length, or null/0 for slots in parameter order
extern const int *const AW_SLOT_MAP[];
extern const int AW_SLOT_MAP_LEN[];
