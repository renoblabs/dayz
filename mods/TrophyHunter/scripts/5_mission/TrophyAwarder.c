// ============================================================
// TrophyAwarder - async orchestration: boss death -> top-damager
// lookup -> item spawn -> provenance stamp -> backend POST.
// Load order : 5_mission (server-side).
// ============================================================
class TrophyAwarder extends TrophyHunterCallback {
    protected ref map<string, ref PendingAward> m_Pending;
    protected ref TrophyHunterClient            m_Client;
    protected ref map<string, string>           m_BossToTrophy;

    void Init(TrophyHunterClient client, map<string, string> bossMap) {
        m_Pending      = new map<string, ref PendingAward>();
        m_Client       = client;
        m_BossToTrophy = bossMap;
    }

    // Called by TrophyHunterMission.OnEntityKilled after allowlist hit.
    void HandleBossKill(EntityAI bossEntity, string bossClassName, string inGameBossId) {
        if (!m_BossToTrophy.Contains(bossClassName)) {
            TrophyHunterConfig.Warn("No trophy mapping for class: " + bossClassName);
            return;
        }
        if (inGameBossId.Length() == 0) {
            TrophyHunterConfig.Warn("Missing in-game boss_id for " + bossClassName + " - skipping.");
            return;
        }
        string trophyClass = m_BossToTrophy.Get(bossClassName);
        string skip        = CollectExistingHolders(trophyClass);

        // Remember what we're awarding for when the async reply comes back.
        string pendingKey = inGameBossId;
        m_Pending.Set(pendingKey, new PendingAward(pendingKey, bossClassName, trophyClass));

        string endpoint = "/api/v1/servers/" + TrophyHunterConfig.SERVER_ID + "/active-boss/" + inGameBossId + "/top-damager";
        if (skip.Length() > 0) endpoint += "?skip_holders=" + skip;
        m_Client.GetTopDamagerAlias(endpoint, this);
    }

    override void OnTopDamagerSuccess(string jsonBody) {
        string encUUID = TrophyJSON.Field(jsonBody, "encounter_id");
        string pid     = TrophyJSON.Field(jsonBody, "player_id");
        string pname   = TrophyJSON.Field(jsonBody, "player_name");

        // Find the matching pending award by iterating (we stored by bossId, not encUUID).
        ref PendingAward pa = TakeFirstPending();
        if (!pa) return;

        PlayerBase player = FindOnlinePlayerById(pid);
        if (!player) {
            TrophyHunterConfig.Warn("Top damager " + pname + " offline - skipping award.");
            PostSkipEvent(encUUID, pa.trophyClass, "top_damager_offline");
            return;
        }

        EntityAI trophy = SpawnTrophyForPlayer(player, pa.trophyClass);
        if (!trophy) {
            PostSkipEvent(encUUID, pa.trophyClass, "spawn_failed");
            return;
        }

        int nowUnix  = (int)GetGame().GetTickTime();
        int graceEnd = nowUnix + TrophyHunterConfig.GRACE_SECONDS;
        string clientNonce = "local-" + encUUID + "-" + pa.trophyClass;

        TrophyProvenance.Stamp(
            trophy, clientNonce, pname, TrophyHunterConfig.SERVER_ID,
            TimeFormatter.NowISO(), graceEnd, pname, TrophyHunterConfig.SERVER_ID);

        Announce(pname, pa.trophyClass);
        PostAwardEvent(encUUID, pa.trophyClass, pa.bossClassName, pid, pname);
    }

    override void OnTopDamagerFailed(string reason) {
        TrophyHunterConfig.Warn("Top-damager lookup failed: " + reason);
        TakeFirstPending();  // clear it so we don't leak
    }

    // ?? Helpers ??????????????????????????????????????????????

    protected ref PendingAward TakeFirstPending() {
        if (!m_Pending || m_Pending.Count() == 0) return null;
        string k = m_Pending.GetKey(0);
        ref PendingAward pa = m_Pending.Get(k);
        m_Pending.Remove(k);
        return pa;
    }

    protected string CollectExistingHolders(string trophyClass) {
        array<Man> players = new array<Man>();
        GetGame().GetPlayers(players);
        string ids = "";
        foreach (Man m : players) {
            PlayerBase pb = PlayerBase.Cast(m);
            if (!pb) continue;
            if (PlayerCarriesTrophy(pb, trophyClass)) {
                if (ids.Length() > 0) ids += ",";
                ids += pb.GetIdentity().GetId();
            }
        }
        return ids;
    }

    protected bool PlayerCarriesTrophy(PlayerBase pb, string trophyClass) {
        array<EntityAI> items = new array<EntityAI>();
        pb.GetInventory().EnumerateInventory(InventoryTraversalType.PREORDER, items);
        foreach (EntityAI item : items) {
            if (item && item.GetType() == trophyClass) return true;
        }
        return false;
    }

    protected PlayerBase FindOnlinePlayerById(string playerId) {
        array<Man> players = new array<Man>();
        GetGame().GetPlayers(players);
        foreach (Man m : players) {
            PlayerBase pb = PlayerBase.Cast(m);
            if (!pb || !pb.GetIdentity()) continue;
            if (pb.GetIdentity().GetId() == playerId) return pb;
        }
        return null;
    }

    protected EntityAI SpawnTrophyForPlayer(PlayerBase pb, string trophyClass) {
        EntityAI t = pb.GetInventory().CreateInInventory(trophyClass);
        if (t) return t;
        vector pos = pb.GetPosition();
        return EntityAI.Cast(GetGame().CreateObject(trophyClass, pos, false, false, true));
    }

    protected void Announce(string playerName, string trophyClass) {
        string msg = playerName + " has claimed the " + TrophyLabel(trophyClass) + " on " + TrophyHunterConfig.SERVER_ID;
        // DEVLOG-TH-004: confirm global-chat broadcast API on first play.
        GetGame().ChatPlayer(msg);
    }

    protected string TrophyLabel(string cls) {
        if (cls == "WarlordsCrown")     return "Warlord's Crown";
        if (cls == "AbominationsJaw")   return "Abomination's Jaw";
        if (cls == "HeavyTankPlate")    return "Heavy Tank Plate";
        if (cls == "NecromancersSkull") return "Necromancer's Skull";
        if (cls == "HuntersFang")       return "Hunter's Fang";
        return cls;
    }

    protected void PostAwardEvent(string encUUID, string trophyClass, string bossClass,
                                  string holderId, string holderName) {
        string body = "{";
        body = body + "\"event_type\":\"trophy.awarded\",";
        body = body + "\"server_id\":\"" + TrophyHunterConfig.SERVER_ID + "\",";
        body = body + "\"server_time\":" + GetGame().GetTime().ToString() + ",";
        body = body + "\"data\":{";
        body = body + "\"encounter_id\":\"" + encUUID + "\",";
        body = body + "\"trophy_class\":\"" + trophyClass + "\",";
        body = body + "\"boss_type\":\"" + bossClass + "\",";
        body = body + "\"holder_id\":\"" + holderId + "\",";
        body = body + "\"holder_name\":\"" + holderName + "\"";
        body = body + "}";
        body = body + "}";
        m_Client.Post("/api/v1/events", body);
    }

    protected void PostSkipEvent(string encUUID, string trophyClass, string reason) {
        string body = "{";
        body = body + "\"event_type\":\"trophy.skipped\",";
        body = body + "\"server_id\":\"" + TrophyHunterConfig.SERVER_ID + "\",";
        body = body + "\"server_time\":" + GetGame().GetTime().ToString() + ",";
        body = body + "\"data\":{";
        body = body + "\"encounter_id\":\"" + encUUID + "\",";
        body = body + "\"trophy_class\":\"" + trophyClass + "\",";
        body = body + "\"reason\":\"" + reason + "\"";
        body = body + "}";
        body = body + "}";
        m_Client.Post("/api/v1/events", body);
    }
}

class PendingAward {
    string encounterKey;
    string bossClassName;
    string trophyClass;

    void PendingAward(string key, string boss, string trophy) {
        encounterKey  = key;
        bossClassName = boss;
        trophyClass   = trophy;
    }
}

// Minimal JSON field extractor. Only for our known server responses.
class TrophyJSON {
    static string Field(string json, string key) {
        string needle = "\"" + key + "\":";
        int idx = json.IndexOf(needle);
        if (idx < 0) return "";
        int start = idx + needle.Length();
        while (start < json.Length() && (json.Get(start) == " " || json.Get(start) == "\"")) start++;
        int end = start;
        while (end < json.Length() && json.Get(end) != "\"" && json.Get(end) != "," && json.Get(end) != "}") end++;
        return json.Substring(start, end - start);
    }
}

class TimeFormatter {
    static string NowISO() {
        int y, mo, d, h, mi, s;
        GetYearMonthDay(y, mo, d);
        GetHourMinuteSecond(h, mi, s);
        return string.Format("%1-%2-%3T%4:%5:%6Z",
            y,
            Pad(mo), Pad(d), Pad(h), Pad(mi), Pad(s));
    }
    static string Pad(int n) {
        string s = n.ToString();
        if (n < 10) s = "0" + s;
        return s;
    }
}
