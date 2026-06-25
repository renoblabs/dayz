// ============================================================
// BossSignalJSON - safe JSON builder utility
// Load order : 4_world
//
// WHY THIS EXISTS:
//   The original dayzAPI mod used raw string concatenation to build
//   JSON. A player name containing a quote or backslash would produce
//   malformed JSON and silently corrupt every event thereafter.
//   This helper always escapes before wrapping in quotes.
//
// DEVLOG-003: String.Replace() API - validate exact Enforce signature.
//   Known candidate: val.Replace(from, to) - check Bohemia wiki.
//   If unavailable, fall back to manual char iteration (see comment below).
// ============================================================

class BossSignalJSON {

    // Wrap a string value safely: escapes \, ", and control chars.
    // Build escape tokens by concatenation - Enforce's 1.29 parser has
    // trouble with "\\\\" and "\\\"" near closing quotes, so keep each
    // literal to at most one escape sequence.
    static string Str(string val) {
        string s = val;

        string BS   = "\\";            // single backslash
        string DQ   = "\"";            // single double-quote
        string BS2  = BS + BS;         // \\
        string BSDQ = BS + DQ;         // \"
        string BSn  = BS + "n";
        string BSr  = BS + "r";
        string BSt  = BS + "t";

        // Order matters: escape backslash first to avoid double-escaping
        s.Replace(BS, BS2);
        s.Replace(DQ, BSDQ);
        s.Replace("\n", BSn);
        s.Replace("\r", BSr);
        s.Replace("\t", BSt);

        return DQ + s + DQ;
    }

    // Float -> JSON number. Uses Enforce's built-in float.ToString()
    // DEVLOG-004: float.ToString() may emit locale-dependent decimal separator.
    //   If RPT shows commas instead of dots, use string formatting alternative.
    static string Num(float val) {
        return val.ToString();
    }

    // Int -> JSON number
    static string Int(int val) {
        return val.ToString();
    }

    // Bool -> JSON boolean literal
    static string Bool(bool val) {
        if (val) return "true";
        return "false";
    }

    // Vector -> JSON object {x, y, z}
    // DayZ vectors: [0]=x, [1]=y, [2]=z
    static string Vec(vector val) {
        return "{\"x\":"  + val[0].ToString() + ",\"y\":" + val[1].ToString() + ",\"z\":" + val[2].ToString() + "}";
    }

    // Null literal
    static string Null() {
        return "null";
    }

    // Build a key:value pair (value already JSON-encoded)
    // e.g. KV("name", Str("vasya")) -> "name":"vasya"
    static string KV(string key, string jsonValue) {
        return "\"" + key + "\":" + jsonValue;
    }

    // Convenience: string key:string value pair
    static string KVStr(string key, string rawVal) {
        return KV(key, Str(rawVal));
    }

    // Convenience: string key:float value pair
    static string KVNum(string key, float val) {
        return KV(key, Num(val));
    }

    // Convenience: string key:int value pair
    static string KVInt(string key, int val) {
        return KV(key, Int(val));
    }

    // Convenience: string key:bool value pair
    static string KVBool(string key, bool val) {
        return KV(key, Bool(val));
    }
};
