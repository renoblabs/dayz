// ============================================================
// BossSignal - Integration example for boss mod authors
//
// This file shows exactly what you add to YOUR boss mod to hook
// into BossSignal. Copy the relevant snippets - don't include
// this file in your PBO.
//
// BossSignal must be listed BEFORE your mod in the -mod= startup line:
//   -mod=@CommunityFramework;@BossSignal;@YourBossMod
// ============================================================


// ?? STEP 1: Register your boss classes at server init ????????
//
// Add this to YOUR modded MissionServer.OnInit(), after super.OnInit():
//
// (Replace classname + display name with your actual boss entity class)

modded class MissionServer {
    override void OnInit() {
        super.OnInit();

        // Register each of your boss classnames here.
        // BossSignal will automatically track kills, timing, and participants.
        BossSignalAPI.RegisterBossClass("YourBossZombie_Base",   "The Warlord");
        BossSignalAPI.RegisterBossClass("YourBossHeavy_Base",    "Iron Giant");
        BossSignalAPI.RegisterBossClass("YourBossNecro_Base",    "The Necromancer");

        // That's it for registration.
    }
};


// ?? STEP 2: Notify BossSignal when a boss spawns ?????????????
//
// In your boss spawn function, after the entity is created and positioned:

/*
void SpawnBoss(string classname, vector position) {
    // ... your existing spawn logic ...
    EntityAI bossEntity = GetGame().CreateObjectEx(classname, position, ECE_CREATEPHYSICS);

    // Add this one line:
    BossSignalAPI.EmitBossSpawned(bossEntity, classname);

    // BossSignal will now:
    //   OK Record the spawn (position, time, player count)
    //   OK Track damage from players (if trackDamage=true in RegisterBossClass)
    //   OK Detect the kill via OnEntityKilled hook
    //   OK Calculate time-to-kill, participants, killer identity
    //   OK Send all of this to the dashboard
}
*/


// ?? OPTIONAL: Notify on programmatic despawn ??????????????????
//
// If your boss can despawn without dying (timer-based, event reset, etc.):

/*
void DespawnBoss(EntityAI bossEntity, string classname) {
    BossSignalAPI.EmitBossDespawned(bossEntity, classname);

    // ... your existing despawn logic ...
    GetGame().ObjectDelete(bossEntity);
}
*/


// ?? OPTIONAL: Custom events ???????????????????????????????????
//
// Send any arbitrary event with boss context:

/*
void OnBossEnrage(EntityAI bossEntity, string classname) {
    string bossId = BossSignalAPI.GetEntityId(bossEntity);

    // extraJsonFields: raw JSON field list (no outer braces)
    BossSignalAPI.EmitCustom(bossId, "boss.phase_changed",
        "\"phase\":2,\"trigger\":\"health_below_30pct\"");
}
*/


// ?? That's the full integration ???????????????????????????????
//
// No other changes needed. BossSignal handles everything else
// via its own MissionServer hooks.
//
// The dashboard will show your boss encounters at http://your-backend:8080
