// ============================================================
// BossSignalTypes - enums, value types, shared structs
// Load order : 3_game
// ============================================================


// ?? Event types sent to the backend ?????????????????????????
// These become the "event_type" field in the JSON payload.
// Keep them lowercase.dot.separated - matches backend DB enum.
// ????????????????????????????????????????????????????????????
// NOTE: Enforce Script enums are int-backed. We use string constants
// instead so the JSON field stays human-readable without a lookup table.
// (DayZ Enforce has no enum-to-string reflection.)
static string BSIG_EVT_BOSS_SPAWNED    = "boss.spawned";
static string BSIG_EVT_BOSS_KILLED     = "boss.killed";
static string BSIG_EVT_BOSS_DESPAWNED  = "boss.despawned";
static string BSIG_EVT_BOSS_DAMAGED    = "boss.damaged";
static string BSIG_EVT_PLAYER_DAMAGE   = "player.boss_damage";
static string BSIG_EVT_HEARTBEAT       = "server.heartbeat";
static string BSIG_EVT_SERVER_START    = "server.started";
static string BSIG_EVT_CUSTOM          = "boss.custom";


// ?? BossRegistration - describes a boss class to BossSignal ??
// Created via BossSignalAPI.RegisterBossClass(...)
// ?????????????????????????????????????????????????????????????
class BossRegistration {
    string m_Classname;         // DayZ entity classname e.g. "ExampleBoss_01"
    string m_DisplayName;       // Human-readable e.g. "The Warlord"
    float  m_HealthThreshold;   // Min MaxHealth to qualify (0 = any entity with this class)
    bool   m_TrackDamage;       // Emit per-hit PLAYER_BOSS_DAMAGE events

    void BossRegistration(string classname, string displayName,
                          float healthThreshold = 0.0, bool trackDamage = true) {
        m_Classname       = classname;
        m_DisplayName     = displayName;
        m_HealthThreshold = healthThreshold;
        m_TrackDamage     = trackDamage;
    }
};


// ?? BossEncounter - live state for a tracked boss entity ?????
// Created when a boss spawns, removed when it dies or despawns.
// Lives in BossSignalEmitter.m_ActiveBosses (keyed by entity ID).
// ?????????????????????????????????????????????????????????????
class BossEncounter {
    string m_BossId;            // String form of entity.GetID() - session-scoped
    string m_BossType;          // Entity classname
    string m_DisplayName;       // From BossRegistration or classname fallback
    float  m_SpawnedAt;         // GetGame().GetTime() at spawn
    float  m_MaxHealth;         // Captured at spawn
    float  m_CurrentHealth;     // Updated on damage events (if enabled)
    vector m_SpawnPosition;     // World position at spawn

    // playerID (Steam64 string) -> cumulative damage dealt this encounter
    ref map<string, float>  m_ParticipantDamage;

    // playerID -> player display name (captured on first damage hit)
    ref map<string, string> m_ParticipantNames;

    void BossEncounter(string bossId, string bossType, string displayName, EntityAI entity) {
        m_BossId              = bossId;
        m_BossType            = bossType;
        m_DisplayName         = displayName;
        m_SpawnedAt           = GetGame().GetTime();
        m_SpawnPosition       = entity.GetPosition();
        m_ParticipantDamage   = new map<string, float>();
        m_ParticipantNames    = new map<string, string>();

        // DEVLOG-002: GetMaxHealth() vs GetHealth("GlobalHealth","Health") - validate on first play.
        // Known-safe fallback: GetHealth("GlobalHealth","Health") is documented in Bohemia wiki.
        m_MaxHealth     = entity.GetHealth("GlobalHealth", "Health");
        m_CurrentHealth = m_MaxHealth;

        BossSignalConfig.Log("Encounter created: " + m_DisplayName + " [" + m_BossType + "] id=" + m_BossId + " hp=" + m_MaxHealth);
    }

    // Record or accumulate damage from a player
    void RecordDamage(string playerId, string playerName, float damage) {
        if (m_ParticipantDamage.Contains(playerId)) {
            m_ParticipantDamage.Set(playerId, m_ParticipantDamage.Get(playerId) + damage);
        } else {
            m_ParticipantDamage.Set(playerId, damage);
            m_ParticipantNames.Set(playerId, playerName);
        }
        m_CurrentHealth = Math.Max(0.0, m_CurrentHealth - damage);
    }

    float GetElapsedSeconds() {
        return GetGame().GetTime() - m_SpawnedAt;
    }

    float GetHealthPct() {
        if (m_MaxHealth <= 0.0) return 1.0;
        return m_CurrentHealth / m_MaxHealth;
    }
};
