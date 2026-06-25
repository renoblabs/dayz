// ============================================================
// TrophyProvenance - stamp/read provenance attributes on a trophy item.
// Load order : 5_mission (server authoritative).
//
// MVP uses an in-memory scratchpad keyed by entity ID. Survives the
// server session. Backend is the long-term source of truth - every
// provenance read can fall back to GET /api/v1/trophies/{id}/history.
//
// DEVLOG-TH-002: validate that a looted trophy retains its entity ID
// across the loot transfer. If not, rehydrate from the backend on
// first GetAttr after a loot event.
// ============================================================
class TrophyProvenance {
    static const string ATTR_ORIGINAL_HOLDER  = "TH_OriginalHolder";
    static const string ATTR_ORIGINAL_SERVER  = "TH_OriginalServer";
    static const string ATTR_ORIGINAL_AT      = "TH_OriginalClaimedAt";
    static const string ATTR_GRACE_UNTIL      = "TH_GraceUntil";
    static const string ATTR_CURRENT_HOLDER   = "TH_CurrentHolder";
    static const string ATTR_CURRENT_SERVER   = "TH_CurrentServer";
    static const string ATTR_TROPHY_ID        = "TH_TrophyId";

    static void Stamp(EntityAI item,
                      string trophyId,
                      string originalHolder,
                      string originalServer,
                      string originalAtISO,
                      int    graceUntilUnix,
                      string currentHolder,
                      string currentServer)
    {
        if (!item) return;
        TrophyAttrScratchpad.Set(item, ATTR_TROPHY_ID,       trophyId);
        TrophyAttrScratchpad.Set(item, ATTR_ORIGINAL_HOLDER, originalHolder);
        TrophyAttrScratchpad.Set(item, ATTR_ORIGINAL_SERVER, originalServer);
        TrophyAttrScratchpad.Set(item, ATTR_ORIGINAL_AT,     originalAtISO);
        TrophyAttrScratchpad.Set(item, ATTR_GRACE_UNTIL,     graceUntilUnix.ToString());
        TrophyAttrScratchpad.Set(item, ATTR_CURRENT_HOLDER,  currentHolder);
        TrophyAttrScratchpad.Set(item, ATTR_CURRENT_SERVER,  currentServer);
    }

    static string Read(EntityAI item, string attr) {
        return TrophyAttrScratchpad.Get(item, attr);
    }

    static bool InGrace(EntityAI item) {
        string g = Read(item, ATTR_GRACE_UNTIL);
        if (g.Length() == 0) return false;
        int until = g.ToInt();
        int now   = (int)GetGame().GetTickTime();
        return now < until;
    }
}

// Simple in-memory store keyed by entity ID.
// Persists for the server session. Rehydrate from backend if needed.
class TrophyAttrScratchpad {
    static ref map<string, ref map<string, string>> s_Data;

    protected static void Ensure() {
        if (!s_Data) s_Data = new map<string, ref map<string, string>>();
    }

    protected static string KeyFor(EntityAI item) {
        if (!item) return "";
        return item.GetID().ToString();
    }

    static void Set(EntityAI item, string attr, string value) {
        Ensure();
        string k = KeyFor(item);
        if (k.Length() == 0) return;
        if (!s_Data.Contains(k)) s_Data.Set(k, new map<string, string>());
        s_Data.Get(k).Set(attr, value);
    }

    static string Get(EntityAI item, string attr) {
        Ensure();
        string k = KeyFor(item);
        if (k.Length() == 0) return "";
        if (!s_Data.Contains(k)) return "";
        map<string, string> bucket = s_Data.Get(k);
        if (!bucket.Contains(attr)) return "";
        return bucket.Get(attr);
    }
}
