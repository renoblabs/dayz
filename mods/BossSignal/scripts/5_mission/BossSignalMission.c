// ============================================================
// BossSignalMission - modded MissionServer
// Load order : 5_mission  (server-side only)
//
// This is the entry point for all server lifecycle hooks.
// It owns the BossSignalEmitter instance and wires it up
// to engine callbacks.
// ============================================================

modded class MissionServer {
    protected ref BossSignalEmitter m_BSigEmitter;
    protected float                  m_BSigHeartbeatTimer;
    protected float                  m_BSigDevTimer;
    protected bool                   m_BSigDevFired;

    void MissionServer() {
        BossSignalConfig.Trace("ctor");
        Print("[BossSignal] MissionServer constructor fired");
    }

    override void OnInit() {
        BossSignalConfig.Trace("oninit_enter");
        Print("[BossSignal] OnInit enter");
        BossSignalConfig.LoadFromProfile();
        super.OnInit();
        BossSignalConfig.Trace("oninit_after_super");

        m_BSigEmitter         = new BossSignalEmitter();
        m_BSigHeartbeatTimer  = 0.0;
        BossSignalConfig.Trace("emitter_constructed");

        m_BSigEmitter.Init();
        BossSignalConfig.Trace("emitter_init_returned");

        BossSignalAPI.s_Emitter = m_BSigEmitter;

        // Example boss registrations. These are placeholder classnames so the
        // mod compiles and runs standalone. Replace them with the actual entity
        // classnames from your own boss mod, or from a licensed boss mod you
        // run (e.g. an external Steam Workshop boss pack). BossSignal does not
        // ship any boss entities of its own.
        BossSignalAPI.RegisterBossClass("ExampleBoss_01",     "Example Boss 01");
        BossSignalAPI.RegisterBossClass("ExampleBoss_02",     "Example Boss 02");
        BossSignalAPI.RegisterBossClass("ExampleBoss_03",     "Example Boss 03");
        BossSignalAPI.RegisterBossClass("ExampleBoss_04",     "Example Boss 04");
        BossSignalAPI.RegisterBossClass("ExampleBoss_05",     "Example Boss 05");
        BossSignalAPI.RegisterBossClass("ExampleBoss_01_500HP", "Example Boss 01 (500 HP)");
        BossSignalAPI.RegisterBossClass("ExampleBoss_02_500HP", "Example Boss 02 (500 HP)");
        BossSignalAPI.RegisterBossClass("ExampleBoss_03_500HP", "Example Boss 03 (500 HP)");
        BossSignalAPI.RegisterBossClass("ExampleBoss_04_500HP", "Example Boss 04 (500 HP)");
        BossSignalAPI.RegisterBossClass("ExampleBoss_05_500HP", "Example Boss 05 (500 HP)");

        BossSignalConfig.Trace("oninit_done");
        Print("[BossSignal] BossSignal v" + BossSignalConfig.VERSION + " active on " + BossSignalConfig.SERVER_ID);
    }

    override void OnMissionStart() {
        BossSignalConfig.Trace("mission_start");
        Print("[BossSignal] OnMissionStart fired");
        super.OnMissionStart();
    }

    override void OnMissionLoaded() {
        BossSignalConfig.Trace("mission_loaded");
        Print("[BossSignal] OnMissionLoaded fired");
        super.OnMissionLoaded();
    }

    void OnEntityKilled(EntityAI victim, EntityAI killer, Man killerPlayer) {
        if (m_BSigEmitter) {
            m_BSigEmitter.OnEntityKilled(victim, killer, killerPlayer);
        }
    }

    override void OnUpdate(float timeslice) {
        super.OnUpdate(timeslice);

        if (!m_BSigEmitter) return;

        m_BSigHeartbeatTimer += timeslice;
        if (m_BSigHeartbeatTimer >= BossSignalConfig.HEARTBEAT_INTERVAL) {
            m_BSigHeartbeatTimer = 0.0;
            m_BSigEmitter.SendHeartbeat();
        }

        if (BossSignalConfig.DEV_SYNTHETIC_ENCOUNTER && !m_BSigDevFired) {
            m_BSigDevTimer += timeslice;
            if (m_BSigDevTimer >= 30.0) {
                m_BSigDevFired = true;
                FireSyntheticEncounter();
            }
        }

        m_BSigEmitter.Tick(timeslice);
    }

    protected void FireSyntheticEncounter() {
        BossSignalConfig.Trace("synth_encounter_fire");
        Print("[BossSignal] Firing synthetic encounter for e2e validation");

        string bossId = "synth-" + Math.RandomInt(1000, 9999).ToString();
        vector spawnPos = "6000 0 7500";
        vector killPos  = "6020 0 7510";

        string spawnFields = BossSignalJSON.KVStr("boss_type", "SyntheticBoss_Base");
        spawnFields += "," + BossSignalJSON.KVStr("boss_display_name", "Synthetic Warlord");
        spawnFields += ",\"spawn_position\":" + BossSignalJSON.Vec(spawnPos);
        spawnFields += "," + BossSignalJSON.KVNum("max_health", 50000);
        spawnFields += "," + BossSignalJSON.KVInt("server_player_count", 0);
        BossSignalAPI.EmitCustom(bossId, "boss.spawned", spawnFields);

        string p1 = "{" + BossSignalJSON.KVStr("player_id", "76561198000000001");
        p1 += "," + BossSignalJSON.KVStr("player_name", "TestKiller");
        p1 += "," + BossSignalJSON.KVNum("damage_dealt", 18500);
        p1 += "," + BossSignalJSON.KVBool("kill_shot", true);
        p1 += "}";

        string p2 = "{" + BossSignalJSON.KVStr("player_id", "76561198000000002");
        p2 += "," + BossSignalJSON.KVStr("player_name", "TestAlly");
        p2 += "," + BossSignalJSON.KVNum("damage_dealt", 22300);
        p2 += "," + BossSignalJSON.KVBool("kill_shot", false);
        p2 += "}";

        string p3 = "{" + BossSignalJSON.KVStr("player_id", "76561198000000003");
        p3 += "," + BossSignalJSON.KVStr("player_name", "TestSniper");
        p3 += "," + BossSignalJSON.KVNum("damage_dealt", 9200);
        p3 += "," + BossSignalJSON.KVBool("kill_shot", false);
        p3 += "}";

        string participants = "[" + p1 + "," + p2 + "," + p3 + "]";

        string killer = "{" + BossSignalJSON.KVStr("player_id", "76561198000000001");
        killer += "," + BossSignalJSON.KVStr("player_name", "TestKiller");
        killer += "," + BossSignalJSON.KVStr("weapon", "AKM");
        killer += "}";

        string killFields = BossSignalJSON.KVStr("boss_type", "SyntheticBoss_Base");
        killFields += "," + BossSignalJSON.KVStr("boss_display_name", "Synthetic Warlord");
        killFields += "," + BossSignalJSON.KVNum("time_to_kill_seconds", 42);
        killFields += "," + BossSignalJSON.KVNum("max_health", 50000);
        killFields += ",\"spawn_position\":" + BossSignalJSON.Vec(spawnPos);
        killFields += ",\"kill_position\":" + BossSignalJSON.Vec(killPos);
        killFields += ",\"killer\":" + killer;
        killFields += ",\"participants\":" + participants;

        BossSignalAPI.EmitCustom(bossId, "boss.killed", killFields);
        BossSignalConfig.Trace("synth_encounter_done");
    }
};
