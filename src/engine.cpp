// One category of airwindows effects as an mpc-vst-plugins engine (wrapper/engine.h): parameter 0 picks the model,
// p1..pN are the model's own controls (renamed per model through dynamic_name/dynamic_display), and the manual tab reads
// the model's documentation page by page (m1..mL, man_page). The models, their docs and the slot counts come from
// generated files (tools/gen_categories.py); this file is the same for every category.
//
// Each model keeps its own settings while you browse: switching back to a model restores what you left it at.
// Saved state names the models, not their list position, so a project still loads the right model after an
// airwindows update adds models to the category.
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
extern "C" {
#include "engine.h"
int mpc_engine_changed(void *inst, char *key, int len);
}
#include "models.h"

extern const char *const AW_DOCS[];   // per model: the manual, pre-wrapped lines separated by '\n' (generated)
extern const char *const AW_WHAT[];   // per model: its one-line description (generated)

#ifndef AW_SLOTS
#error "AW_SLOTS (the category's largest parameter count) comes from the generated params"
#endif
#define DOC_LINES 12   // readout lines on a manual page (m1..m12)

namespace {

struct inst_t {
    int model = -1;
    AirwinConsolidatedBase *fx = nullptr;
    std::vector<std::vector<float>> vals;   // per model: its settings, empty until it was first used
    int page = 0;
    std::vector<std::string> doc;            // the current model's manual lines
    std::vector<std::string> changed;        // keys to report to the host (mpc_engine_changed)
    std::chrono::steady_clock::time_point last_step{};   // the last accepted step-button press
};

int nparams(const inst_t *s) { return s->model >= 0 ? AW_MODELS[s->model].num_params() : 0; }

int pages(const inst_t *s) { return s->doc.empty() ? 1 : (int)(s->doc.size() + DOC_LINES - 1) / DOC_LINES; }

void report_all(inst_t *s) {
    s->changed.clear();
    for (int i = 1; i <= AW_SLOTS; i++) s->changed.push_back("p" + std::to_string(i));
    s->changed.push_back("man_page");
}

void load_doc(inst_t *s) {
    s->doc.clear();
    const char *d = AW_DOCS[s->model];
    while (*d) {
        const char *e = strchr(d, '\n');
        if (!e) e = d + strlen(d);
        s->doc.emplace_back(d, e - d);
        d = *e ? e + 1 : e;
    }
}

void select_model(inst_t *s, int m) {
    if (m < 0) m = 0;
    if (m >= AW_NUM_MODELS) m = AW_NUM_MODELS - 1;
    if (m == s->model && s->fx) return;
    AirwinConsolidatedBase *fx = AW_MODELS[m].create();
    fx->setSampleRate(44100.f);
    std::vector<float> &v = s->vals[m];
    if (v.empty())
        for (int i = 0; i < AW_MODELS[m].num_params(); i++) v.push_back(fx->getParameter(i));
    else
        for (int i = 0; i < (int)v.size(); i++) fx->setParameter(i, v[i]);
    delete s->fx;
    s->fx = fx;
    s->model = m;
    s->page = 0;
    load_doc(s);
    report_all(s);
}

int find_model(const char *name, size_t len) {
    for (int i = 0; i < AW_NUM_MODELS; i++)
        if (strlen(AW_MODELS[i].name) == len && !strncmp(AW_MODELS[i].name, name, len)) return i;
    return -1;
}

int slot_of(const char *key, const char *suffix) {   // "p3" / "p3_name" -> 3, else 0
    if (key[0] != 'p' || key[1] < '1' || key[1] > '9') return 0;
    char *end;
    long n = strtol(key + 1, &end, 10);
    if (strcmp(end, suffix) || n < 1 || n > AW_SLOTS) return 0;
    return (int)n;
}

// state: "cur=<model>;<model>=v,v,v;<model>=v,..." (every model touched this session, by name)
std::string save_state(const inst_t *s) {
    std::string o = "cur=" + std::string(AW_MODELS[s->model].name);
    for (int m = 0; m < AW_NUM_MODELS; m++) {
        if (s->vals[m].empty()) continue;
        o += ";" + std::string(AW_MODELS[m].name) + "=";
        for (size_t i = 0; i < s->vals[m].size(); i++) {
            char b[24];
            snprintf(b, sizeof b, "%s%.6g", i ? "," : "", s->vals[m][i]);
            o += b;
        }
    }
    return o;
}

void load_state(inst_t *s, const char *st) {
    int cur = -1;
    while (*st) {
        const char *end = strchr(st, ';');
        if (!end) end = st + strlen(st);
        const char *eq = (const char *)memchr(st, '=', end - st);
        if (eq) {
            if (eq - st == 3 && !strncmp(st, "cur", 3)) {
                cur = find_model(eq + 1, end - eq - 1);
            } else {
                int m = find_model(st, eq - st);
                if (m >= 0) {
                    std::vector<float> v;
                    for (const char *p = eq + 1; p < end;) {
                        char *q;
                        float f = strtof(p, &q);
                        if (q == p) break;
                        v.push_back(f < 0 ? 0 : f > 1 ? 1 : f);
                        p = *q == ',' ? q + 1 : q;
                    }
                    v.resize(AW_MODELS[m].num_params(), 0.5f);   // a model that gained controls keeps the rest
                    s->vals[m] = v;
                }
            }
        }
        st = *end ? end + 1 : end;
    }
    if (cur < 0) cur = s->model >= 0 ? s->model : 0;
    s->model = -1;   // force the reload, with the restored values
    select_model(s, cur);
}

void *create(const char *) {
    AirwinConsolidatedBase::defaultSampleRate = 44100.f;
    inst_t *s = new inst_t;
    s->vals.resize(AW_NUM_MODELS);
    select_model(s, 0);
    return s;
}

void destroy(void *p) {
    inst_t *s = (inst_t *)p;
    delete s->fx;
    delete s;
}

void midi(void *, const uint8_t *, int) {}

// The skin's step buttons (momentary params): a press steps the model (wrapping) or the manual page (stopping at the
// ends). A host can deliver one touch twice, so presses closer than STEP_DEBOUNCE_MS count once.
#define STEP_DEBOUNCE_MS 250
bool step_press(inst_t *s, const char *key, const char *val) {
    int model_d = !strcmp(key, "model_prev") ? -1 : !strcmp(key, "model_next") ? 1 : 0;
    int page_d = !strcmp(key, "page_prev") ? -1 : !strcmp(key, "page_next") ? 1 : 0;
    if (!model_d && !page_d) return false;
    if (strtof(val, nullptr) <= 0.5f) return true;                      // the release
    auto now = std::chrono::steady_clock::now();
    if (now - s->last_step < std::chrono::milliseconds(STEP_DEBOUNCE_MS)) return true;
    s->last_step = now;
    if (model_d) {
        select_model(s, (s->model + model_d + AW_NUM_MODELS) % AW_NUM_MODELS);
        s->changed.push_back("model");
    } else {
        int pg = s->page + page_d;
        s->page = pg < 0 ? 0 : pg >= pages(s) ? pages(s) - 1 : pg;
        s->changed.push_back("man_page");
    }
    return true;
}

void set_param(void *p, const char *key, const char *val) {
    inst_t *s = (inst_t *)p;
    if (step_press(s, key, val)) return;
    if (!strcmp(key, "model")) { select_model(s, atoi(val)); return; }
    if (!strcmp(key, "state")) { load_state(s, val); return; }
    if (!strcmp(key, "man_page")) {
        int pg = atoi(val), n = pages(s);
        s->page = pg < 0 ? 0 : pg >= n ? n - 1 : pg;
        return;
    }
    int k = slot_of(key, "");
    if (k && k <= nparams(s)) {
        float f = strtof(val, nullptr);
        f = f < 0 ? 0 : f > 1 ? 1 : f;
        s->vals[s->model][k - 1] = f;
        s->fx->setParameter(k - 1, f);
    }
}

int put(char *buf, int len, const std::string &t) {
    snprintf(buf, len, "%s", t.c_str());
    return 1;
}

std::string trim(const char *t) {
    std::string s(t);
    size_t a = s.find_first_not_of(' '), b = s.find_last_not_of(' ');
    return a == std::string::npos ? "" : s.substr(a, b - a + 1);
}

int get_param(void *p, const char *key, char *buf, int len) {
    inst_t *s = (inst_t *)p;
    if (!strcmp(key, "model")) return put(buf, len, std::to_string(s->model));
    if (!strcmp(key, "state")) return put(buf, len, save_state(s));
    if (!strcmp(key, "man_page")) return put(buf, len, std::to_string(s->page));
    if (!strcmp(key, "info")) return put(buf, len, AW_WHAT[s->model]);
    if (!strcmp(key, "man_info"))
        return put(buf, len, std::string("page ") + std::to_string(s->page + 1) + " / " +
                                 std::to_string(pages(s)));
    if (key[0] == 'm' && key[1] >= '1' && key[1] <= '9') {
        int l = atoi(key + 1);
        if (l >= 1 && l <= DOC_LINES) {
            size_t i = (size_t)s->page * DOC_LINES + l - 1;
            return put(buf, len, i < s->doc.size() ? s->doc[i] : " ");
        }
    }
    int k;
    if ((k = slot_of(key, ""))) return put(buf, len, k <= nparams(s) ? std::to_string(s->vals[s->model][k - 1]) : "0");
    if ((k = slot_of(key, "_name"))) {
        if (k > nparams(s)) return put(buf, len, " ");
        char t[256] = "";
        s->fx->getParameterName(k - 1, t);
        return put(buf, len, trim(t));
    }
    if ((k = slot_of(key, "_display"))) {
        if (k > nparams(s)) return put(buf, len, " ");
        char d[256] = "", l[256] = "";
        s->fx->getParameterDisplay(k - 1, d);
        s->fx->getParameterLabel(k - 1, l);
        std::string t = trim(d), u = trim(l);
        return put(buf, len, u.empty() ? t : t + " " + u);
    }
    return 0;
}

void render(void *, int16_t *out, int frames) { memset(out, 0, frames * 4); }

void process_float(void *p, float *const *in, float *const *out, int frames) {
    inst_t *s = (inst_t *)p;
    s->fx->processReplacing((float **)in, (float **)out, frames);
}

const mpc_engine_t ENGINE = {create, destroy, midi, set_param, get_param, render, nullptr, nullptr, process_float};

}   // namespace

extern "C" const mpc_engine_t *mpc_engine(void) { return &ENGINE; }

extern "C" int mpc_engine_changed(void *p, char *key, int len) {
    inst_t *s = (inst_t *)p;
    if (s->changed.empty()) return 0;
    snprintf(key, len, "%s", s->changed.back().c_str());
    s->changed.pop_back();
    return 1;
}
