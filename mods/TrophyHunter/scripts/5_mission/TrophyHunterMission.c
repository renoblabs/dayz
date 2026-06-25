// ============================================================
// TrophyHunterMission - mission hook (server-only, load order 5_mission).
//
// Subclasses MissionServer. Loads the allowlist at OnInit, then on
// OnEntityKilled checks the dead entity's class against it and, on hit,
// kicks off TrophyAwarder.
// ============================================================
modded class MissionServer {
    ref TrophyHunterClient m_TH_Client;
    ref TrophyAwarder      m_TH_Awarder;
    ref map<string,string> m_TH_BossMap;

    override void OnInit() {
        super.OnInit();
        TrophyHunterConfig.Load();

        m_TH_BossMap = LoadBossMap(TrophyHunterConfig.BOSSES_JSON_PATH);
        if (m_TH_BossMap.Count() == 0) {
            TrophyHunterConfig.Err("Boss allowlist is empty. Edit config/bosses.json and restart.");
            return;
        }

        m_TH_Client  = new TrophyHunterClient();
        if (!m_TH_Client.IsReady()) {
            TrophyHunterConfig.Err("REST client not ready - trophies disabled.");
            return;
        }

        m_TH_Awarder = new TrophyAwarder();
        m_TH_Awarder.Init(m_TH_Client, m_TH_BossMap);

        TrophyHunterConfig.Log("Ready. Watching " + m_TH_BossMap.Count() + " boss classes.");
    }

    override void OnEntityKilled(EntityAI victim, EntityAI killer, Man killerPlayer) {
        super.OnEntityKilled(victim, killer, killerPlayer);
        if (!victim || !m_TH_Awarder) return;

        string cls = victim.GetType();
        if (!m_TH_BossMap.Contains(cls)) return;

        string bossId = BossSignalAPI.GetEncounterIdForBoss(victim);
        m_TH_Awarder.HandleBossKill(victim, cls, bossId);
    }

    protected map<string,string> LoadBossMap(string path) {
        map<string,string> result = new map<string,string>();
        ref BossMapFile f = new BossMapFile();
        string errMsg;
        if (!JsonFileLoader<ref BossMapFile>.LoadFile(path, f, errMsg) || !f.bosses) {
            TrophyHunterConfig.Err("Failed to load " + path);
            return result;
        }
        foreach (BossMapEntry e : f.bosses) {
            if (e.cls.Length() > 0 && e.trophy.Length() > 0) result.Set(e.cls, e.trophy);
        }
        return result;
    }
};

class BossMapFile {
    ref array<ref BossMapEntry> bosses;
}

// DEVLOG-TH-005: if "class" JSON key trips the Enforce parser, rename
// the JSON key to "classname" and the field name below to match.
class BossMapEntry {
    string cls;
    string trophy;
}
