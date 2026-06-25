// ============================================================
// BossSignalEmitter - core encounter tracking + event emission
// Load order : 5_mission  (server-side only)
//
// This class is the engine room. It:
//   1. Maintains a map of live boss encounters
//   2. Is called by modded MissionServer on entity kill
//   3. Builds JSON payloads via BossSignalJSON helpers
//   4. Hands payloads off to BossSignalClient for HTTP delivery
//
// DEVLOG ITEMS IN THIS FILE:
//   DEVLOG-010: GetGame().GetPlayers() vs GetPlayerList() - see SendHeartbeat()
//   DEVLOG-011: PlayerBase.GetIdentity().GetPlayerId() vs .GetId() - see ExtractPlayerInfo()
//   DEVLOG-012: entity.GetItemInHands() return type - see ExtractKillerInfo()
//   DEVLOG-013: map<K,V>.GetKey(i) / .GetElement(i) iteration - see BuildParticipantsArray()
// ============================================================

class BossSignalEmitter {
    // HTTP client
    protected ref BossSignalClient m_Client;

    // Live boss encounters: entityId -> BossEncounter
    protected ref map<string, ref BossEncounter> m_ActiveBosses;

    // ?? Init ?????????????????????????????????????????????????
    void Init() {
        BossSignalConfig.Trace("emitter_init_enter");
        m_Client       = new BossSignalClient();
        BossSignalConfig.Trace("emitter_client_new");
        m_ActiveBosses = new map<string, ref BossEncounter>();

        BossSignalConfig.Load();
        BossSignalConfig.Trace("emitter_config_loaded");

        if (!m_Client.IsReady()) {
            BossSignalConfig.Trace("emitter_client_NOT_ready");
            BossSignalConfig.Err("HTTP client failed to initialise - events will be dropped." + " Check BACKEND_URL and server network access.");
        } else {
            BossSignalConfig.Trace("emitter_client_ready");
        }

        SendServerStartup();
        BossSignalConfig.Trace("emitter_sent_startup");
        BossSignalConfig.Log("Emitter ready.");
    }

    // ?? Tick - called from MissionServer.OnUpdate ?????????????
    void Tick(float timeslice) {
        if (m_Client) m_Client.Tick();
    }

    // ?? OnEntityKilled - called by modded MissionServer ???????
    // DEVLOG-010-a: Exact parameter types may vary between DayZ versions.
    //   Known signature variants:
    //     (EntityAI victim, EntityAI killer, Man killerPlayer)
    //     (IEntity victim, IEntity killer, DamageResult damage, ...)
    //   We receive EntityAI casted types from the modded class layer.
    void OnEntityKilled(EntityAI victim, EntityAI killer, Man killerPlayer) {
        if (!victim) return;

        string classname = victim.GetType();
        string bossId    = victim.GetID().ToString();

        bool isTracked    = m_ActiveBosses.Contains(bossId);
        bool isRegistered = BossSignalAPI.IsRegistered(classname);

        if (!isTracked && !isRegistered) return;

        HandleBossKilled(victim, killer, killerPlayer, bossId, classname);
    }

    // ?? OnBossSpawned - called by BossSignalAPI ???????????????
    void OnBossSpawned(EntityAI entity, string classname) {
        if (!entity) return;

        string bossId = entity.GetID().ToString();
        if (m_ActiveBosses.Contains(bossId)) {
            BossSignalConfig.Warn("Duplicate spawn event for bossId=" + bossId + " - ignoring.");
            return;
        }

        // Look up display name from registry
        string displayName = classname;
        BossRegistration reg = BossSignalAPI.GetRegistration(classname);
        if (reg) displayName = reg.m_DisplayName;

        ref BossEncounter enc = new BossEncounter(bossId, classname, displayName, entity);
        m_ActiveBosses.Set(bossId, enc);

        SendBossSpawned(enc);
    }

    // ?? OnBossDespawned - called by BossSignalAPI ?????????????
    void OnBossDespawned(EntityAI entity, string classname) {
        if (!entity) return;

        string bossId = entity.GetID().ToString();
        BossEncounter enc;
        if (m_ActiveBosses.Contains(bossId)) {
            enc = m_ActiveBosses.Get(bossId);
        }

        string displayName = classname;
        if (enc) displayName = enc.m_DisplayName;

        string payload = BuildBasePayload(BSIG_EVT_BOSS_DESPAWNED);
        payload += ",\"data\":{" + BossSignalJSON.KVStr("boss_id", bossId) + "," + BossSignalJSON.KVStr("boss_type", classname) + "," + BossSignalJSON.KVStr("boss_display_name", displayName);
        if (enc) {
            payload += "," + BossSignalJSON.KVNum("elapsed_seconds", enc.GetElapsedSeconds());
            payload += "," + BossSignalJSON.KVNum("health_pct", enc.GetHealthPct());
        }
        payload += "}}";

        m_Client.Post("/api/v1/events", BSIG_EVT_BOSS_DESPAWNED, payload);

        if (m_ActiveBosses.Contains(bossId)) m_ActiveBosses.Remove(bossId);
    }

    // ?? OnCustomBossEvent - called by BossSignalAPI.EmitCustom ?
    void OnCustomBossEvent(string bossId, string eventType, string extraJsonFields) {
        string payload = BuildBasePayload(BSIG_EVT_CUSTOM);
        payload += ",\"data\":{" + BossSignalJSON.KVStr("boss_id", bossId) + "," + BossSignalJSON.KVStr("custom_event_type", eventType);
        if (extraJsonFields.Length() > 0) {
            payload += "," + extraJsonFields;
        }
        payload += "}}";

        m_Client.Post("/api/v1/events", eventType, payload);
    }

    // ?? SendHeartbeat - called from MissionServer timer ???????
    void SendHeartbeat() {
        int playerCount = GetCurrentPlayerCount();

        string activeBossArr = "[";
        bool first = true;
        for (int i = 0; i < m_ActiveBosses.Count(); i++) {
            // DEVLOG-013: map iteration - validate GetKey()/GetElement() on first play
            string bossId    = m_ActiveBosses.GetKey(i);
            BossEncounter enc = m_ActiveBosses.GetElement(i);
            if (!first) activeBossArr += ",";

            activeBossArr += "{";
            activeBossArr += BossSignalJSON.KVStr("boss_id", bossId) + ",";
            activeBossArr += BossSignalJSON.KVStr("boss_type", enc.m_BossType) + ",";
            activeBossArr += BossSignalJSON.KVStr("display_name", enc.m_DisplayName) + ",";
            activeBossArr += BossSignalJSON.KVNum("elapsed_seconds", enc.GetElapsedSeconds()) + ",";
            activeBossArr += BossSignalJSON.KVNum("health_pct", enc.GetHealthPct()) + ",";
            activeBossArr += BossSignalJSON.KVInt("participant_count", enc.m_ParticipantDamage.Count());
            activeBossArr += "}";
            first = false;
        }
        activeBossArr += "]";

        string payload = BuildBasePayload(BSIG_EVT_HEARTBEAT);
        payload += ",\"data\":{";
        payload += BossSignalJSON.KVInt("player_count", playerCount) + ",";
        payload += BossSignalJSON.KVInt("active_boss_count", m_ActiveBosses.Count()) + ",";
        payload += "\"active_bosses\":" + activeBossArr;
        payload += "}}";

        m_Client.Post("/api/v1/events", BSIG_EVT_HEARTBEAT, payload);
    }

    // ?? Private: handle confirmed boss kill ???????????????????
    protected void HandleBossKilled(EntityAI victim, EntityAI killer,
                                    Man killerPlayer, string bossId, string classname) {
        BossEncounter enc;
        if (m_ActiveBosses.Contains(bossId)) {
            enc = m_ActiveBosses.Get(bossId);
        }

        string displayName = classname;
        vector spawnPos    = victim.GetPosition();
        float  maxHealth   = victim.GetHealth("GlobalHealth", "Health");
        float  ttk         = 0.0;

        if (enc) {
            displayName = enc.m_DisplayName;
            spawnPos    = enc.m_SpawnPosition;
            maxHealth   = enc.m_MaxHealth;
            ttk         = enc.GetElapsedSeconds();
        }

        // Extract killer info
        ref KillerInfo ki = new KillerInfo();
        ExtractKillerInfo(killerPlayer, ki);
        string killerPlayerId   = ki.m_PlayerId;
        string killerPlayerName = ki.m_PlayerName;
        string killerWeapon     = ki.m_WeaponClass;

        // Build participants block
        string participantsArr = BuildParticipantsArray(enc, killerPlayerId);

        // Build payload - split to avoid Enforce 'Formula too complex'
        string payload = BuildBasePayload(BSIG_EVT_BOSS_KILLED);
        payload += ",\"data\":{";
        payload += BossSignalJSON.KVStr("boss_id", bossId) + ",";
        payload += BossSignalJSON.KVStr("boss_type", classname) + ",";
        payload += BossSignalJSON.KVStr("boss_display_name", displayName) + ",";
        payload += BossSignalJSON.KVNum("time_to_kill_seconds", ttk) + ",";
        payload += BossSignalJSON.KVNum("max_health", maxHealth) + ",";
        payload += "\"spawn_position\":" + BossSignalJSON.Vec(spawnPos) + ",";
        payload += "\"kill_position\":" + BossSignalJSON.Vec(victim.GetPosition()) + ",";
        payload += "\"killer\":{";
        payload += BossSignalJSON.KVStr("player_id", killerPlayerId) + ",";
        payload += BossSignalJSON.KVStr("player_name", killerPlayerName) + ",";
        payload += BossSignalJSON.KVStr("weapon", killerWeapon);
        payload += "},";
        payload += "\"participants\":" + participantsArr;
        payload += "}}";

        m_Client.Post("/api/v1/events", BSIG_EVT_BOSS_KILLED, payload);

        int pcount = 0;
        if (enc) pcount = enc.m_ParticipantDamage.Count();
        BossSignalConfig.Log("Boss killed: " + displayName + " by " + killerPlayerName + " | TTK=" + Math.Round(ttk) + "s" + " | " + pcount + " participants");

        // Cleanup
        if (m_ActiveBosses.Contains(bossId)) m_ActiveBosses.Remove(bossId);
    }

    // ?? Private: server startup event ????????????????????????
    protected void SendServerStartup() {
        string payload = BuildBasePayload(BSIG_EVT_SERVER_START);
        payload += ",\"data\":{";
        payload += BossSignalJSON.KVStr("bosssignal_version", BossSignalConfig.VERSION) + ",";
        payload += "\"loaded_mods\":" + BuildLoadedModsArray();
        payload += "}}";
        m_Client.Post("/api/v1/events", BSIG_EVT_SERVER_START, payload);
    }

    // Enumerate child class names under CfgMods -> JSON array of strings.
    // Each loaded mod registers a class under CfgMods (BossSignal itself does
    // this in its own config.cpp - "class CfgMods { class BossSignal { ... } }").
    // We emit the raw class name (e.g. "BossSignal"), not the addon folder name
    // (e.g. "@BossSignal"); the backend accepts either form.
    // Returns "[]" if the engine reports 0 children for any reason, so the
    // server.started event still succeeds.
    protected string BuildLoadedModsArray() {
        string arr = "[";
        int childCount = GetGame().ConfigGetChildrenCount("CfgMods");
        bool first = true;
        for (int i = 0; i < childCount; i++) {
            string name;
            GetGame().ConfigGetChildName("CfgMods", i, name);
            if (name.Length() == 0) continue;
            if (!first) arr += ",";
            arr += BossSignalJSON.Str(name);
            first = false;
        }
        arr += "]";
        return arr;
    }

    // ?? Private: boss spawned event ???????????????????????????
    protected void SendBossSpawned(BossEncounter enc) {
        int playerCount = GetCurrentPlayerCount();

        string payload = BuildBasePayload(BSIG_EVT_BOSS_SPAWNED);
        payload += ",\"data\":{";
        payload += BossSignalJSON.KVStr("boss_id", enc.m_BossId) + ",";
        payload += BossSignalJSON.KVStr("boss_type", enc.m_BossType) + ",";
        payload += BossSignalJSON.KVStr("boss_display_name", enc.m_DisplayName) + ",";
        payload += "\"spawn_position\":" + BossSignalJSON.Vec(enc.m_SpawnPosition) + ",";
        payload += BossSignalJSON.KVNum("max_health", enc.m_MaxHealth) + ",";
        payload += BossSignalJSON.KVInt("server_player_count", playerCount);
        payload += "}}";

        m_Client.Post("/api/v1/events", BSIG_EVT_BOSS_SPAWNED, payload);
    }

    // ?? Private: extract killer player info ???????????????????
    // DEVLOG-011: RESOLVED. PlayerIdentity API in DayZ 1.29:
    //   .GetId()   -> string (Steam64 ID) - confirmed via CF source
    //   .GetName() -> string (character name)
    // DEVLOG-012: GetItemInHands() return type
    //   May be: ItemBase, EntityAI, or HumanItemBehaviorCB
    //   Cast to EntityAI and call GetType() for classname
    protected void ExtractKillerInfo(Man killerPlayer, KillerInfo info) {
        info.m_PlayerId   = "";
        info.m_PlayerName = "Unknown";
        info.m_WeaponClass = "";

        if (!killerPlayer) return;

        PlayerBase pb = PlayerBase.Cast(killerPlayer);
        if (pb) {
            PlayerIdentity identity = pb.GetIdentity();
            if (identity) {
                info.m_PlayerId   = identity.GetId();
                info.m_PlayerName = identity.GetName();
            }
            EntityAI inHands = EntityAI.Cast(pb.GetItemInHands());
            if (inHands) info.m_WeaponClass = inHands.GetType();
        }
    }

    // ?? Private: build participants JSON array ?????????????????
    // DEVLOG-013: map.GetKey(i) + .GetElement(i) - validate on first play.
    //   Alternative if unavailable: convert to array<string> first via map.GetKeyArray()
    protected string BuildParticipantsArray(BossEncounter enc, string killerPlayerId) {
        string arr = "[";
        if (!enc || !enc.m_ParticipantDamage) return arr + "]";

        bool first = true;
        for (int i = 0; i < enc.m_ParticipantDamage.Count(); i++) {
            string pid = enc.m_ParticipantDamage.GetKey(i);      // DEVLOG-013
            float  dmg = enc.m_ParticipantDamage.GetElement(i);  // DEVLOG-013

            string name = "Unknown";
            if (enc.m_ParticipantNames.Contains(pid)) {
                name = enc.m_ParticipantNames.Get(pid);
            }

            if (!first) arr += ",";
            bool isKillShot = (pid == killerPlayerId);
            arr += "{";
            arr += BossSignalJSON.KVStr("player_id", pid) + ",";
            arr += BossSignalJSON.KVStr("player_name", name) + ",";
            arr += BossSignalJSON.KVNum("damage_dealt", dmg) + ",";
            arr += BossSignalJSON.KVBool("kill_shot", isKillShot);
            arr += "}";
            first = false;
        }
        return arr + "]";
    }

    // ?? Private: base payload envelope ???????????????????????
    // Every event shares this outer structure.
    // Caller appends ,\"data\":{...}} to close.
    protected string BuildBasePayload(string eventType) {
        string p = "{" + BossSignalJSON.KVStr("event_type", eventType) + "," + BossSignalJSON.KVStr("server_id", BossSignalConfig.SERVER_ID) + "," + BossSignalJSON.KVNum("server_time", GetGame().GetTime()) + "," + BossSignalJSON.KVStr("version", BossSignalConfig.VERSION);
        return p;
    }

    // Integration hook for TrophyHunter.
    string GetEncounterIdForBoss(EntityAI bossEntity) {
        if (!bossEntity) return "";
        string bossId = bossEntity.GetID().ToString();
        if (!m_ActiveBosses.Contains(bossId)) return "";
        BossEncounter enc = m_ActiveBosses.Get(bossId);
        if (!enc) return "";
        return enc.m_BossId;
    }

    // ?? Private: player count helper ?????????????????????????
    // DEVLOG-010: GetGame().GetPlayers() API - validate exact signature on first play.
    //   Options seen in community mods:
    //     GetGame().GetPlayers(TManArray outArray)         -> fills array, returns void
    //     GetGame().GetWorld().GetPlayers(TManArray array) -> alternative
    //   TManArray is likely defined as array<Man> or ref to it.
    protected int GetCurrentPlayerCount() {
        array<Man> players = new array<Man>();
        GetGame().GetPlayers(players);  // DEVLOG-010
        return players.Count();
    }
};

class KillerInfo {
    string m_PlayerId;
    string m_PlayerName;
    string m_WeaponClass;
}
