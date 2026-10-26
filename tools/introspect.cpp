// Host-side probe: instantiate every model and print its parameters as JSON lines, for tools/gen_categories.py.
// Per parameter: name, label, default value and display, and the distinct display strings over a 0..1 sweep
// (few distinct strings = a stepped control, drawn as a selector knob).
#include <cstdio>
#include <set>
#include <string>
#include <vector>
#include "models.h"

static std::string esc(const char *s) {
    std::string o;
    for (; *s; s++) {
        unsigned char c = *s;
        if (c == '"' || c == '\\') { o += '\\'; o += c; }
        else if (c < 0x20) o += ' ';
        else o += c;
    }
    return o;
}

static std::string trim(const char *s) {
    std::string t(s);
    size_t a = t.find_first_not_of(' '), b = t.find_last_not_of(' ');
    return a == std::string::npos ? "" : t.substr(a, b - a + 1);
}

int main() {
    AirwinConsolidatedBase::defaultSampleRate = 44100.f;
    for (int i = 0; i < AW_NUM_MODELS; i++) {
        AirwinConsolidatedBase *fx = AW_MODELS[i].create();
        fx->setSampleRate(44100.f);
        std::vector<std::string> ps;
        for (int p = 0; p < AW_MODELS[i].num_params(); p++) {
            char name[256] = "";
            fx->getParameterName(p, name);
            float def = fx->getParameter(p);
            char lab[256] = "", disp[256] = "";
            fx->getParameterLabel(p, lab);
            fx->getParameterDisplay(p, disp);
            std::vector<std::string> steps;
            std::set<std::string> seen;
            for (int k = 0; k <= 200 && steps.size() <= 16; k++) {
                char d[256] = "";
                fx->setParameter(p, k / 200.f);
                fx->getParameterDisplay(p, d);
                std::string s = trim(d);
                if (seen.insert(s).second) steps.push_back(s);
            }
            fx->setParameter(p, def);
            std::string j = "{\"name\":\"" + esc(name) + "\",\"label\":\"" + esc(trim(lab).c_str()) + "\",\"default\":" +
                            std::to_string(def) + ",\"display\":\"" + esc(trim(disp).c_str()) + "\",\"steps\":[";
            if (steps.size() <= 16)
                for (size_t k = 0; k < steps.size(); k++) j += (k ? ",\"" : "\"") + esc(steps[k].c_str()) + "\"";
            j += "]}";
            ps.push_back(j);
        }
        printf("{\"name\":\"%s\",\"params\":[", AW_MODELS[i].name);
        for (size_t k = 0; k < ps.size(); k++) printf("%s%s", k ? "," : "", ps[k].c_str());
        printf("]}\n");
        delete fx;
    }
    return 0;
}
