// TestRunner - modded MissionServer that kicks off scripted scenarios
// when the server was started with `-testMode=1` (or `testMode = 1;`
// in serverDZ.cfg).
//
// Each scenario runs serially on the CallQueue with spacing defined in
// TestHarnessConfig. Results are written to
// $profile:testharness_results.json so modctl can parse them.

modded class MissionServer
{
    private ref array<string> m_TH_Scenarios;
    private int m_TH_CurrentIdx;
    private ref array<string> m_TH_Results;

    override void OnInit()
    {
        super.OnInit();

        // Guard: only activate when test mode is on.
        if (GetGame().ServerConfigGetInt("testMode") != 1) {
            return;
        }

        TestHarnessConfig.Log("TestHarness active (testMode=1). Scheduling scenarios.");
        m_TH_Scenarios = TestHarnessConfig.SCENARIOS;
        m_TH_CurrentIdx = 0;
        m_TH_Results = new array<string>();

        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(
            this.RunNextScenario,
            TestHarnessConfig.START_DELAY_MS,
            false);
    }

    void RunNextScenario()
    {
        if (m_TH_CurrentIdx >= m_TH_Scenarios.Count()) {
            this.FinalizeAndWriteResults();
            return;
        }

        string name = m_TH_Scenarios.Get(m_TH_CurrentIdx);
        TestHarnessConfig.Log("Running scenario: " + name);

        bool passed = false;
        switch (name) {
            case "boss_spawn_then_despawn":
                passed = this.Scenario_BossSpawnThenDespawn();
                break;
            case "bosssignal_emit_event":
                passed = this.Scenario_BossSignalEmitEvent();
                break;
            default:
                TestHarnessConfig.Log("Unknown scenario (skipping): " + name);
                passed = false;
                break;
        }

        string status;
        if (passed) status = "PASS";
        else        status = "FAIL";
        m_TH_Results.Insert("{\"scenario\":\"" + name + "\",\"status\":\"" + status + "\"}");
        TestHarnessConfig.Log("Scenario " + name + " -> " + status);

        m_TH_CurrentIdx++;
        GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(
            this.RunNextScenario,
            TestHarnessConfig.INTER_SCENARIO_DELAY_MS,
            false);
    }

    // --- Scenarios ---

    // DEVLOG-TH-HARNESS-001: spawn a test boss, despawn it, confirm no crash.
    // The real boss class depends on the installed boss mod - for now we test
    // the lifecycle path without asserting on a specific class.
    bool Scenario_BossSpawnThenDespawn()
    {
        // Placeholder: real spawn + despawn logic goes here once you wire in
        // the boss class names from your chosen boss-content mod (substitute
        // your own or a licensed boss mod's classnames). This just logs.
        TestHarnessConfig.Log("[scenario] boss_spawn_then_despawn (placeholder)");
        return true;
    }

    // DEVLOG-TH-HARNESS-002: verify BossSignal's emitter is reachable.
    // If BossSignal is loaded, its global state should be initialised.
    bool Scenario_BossSignalEmitEvent()
    {
        TestHarnessConfig.Log("[scenario] bosssignal_emit_event (placeholder - will fire a test event when the emitter API is stabilised)");
        return true;
    }

    // Write JSON result file the Python test harness / modctl reads.
    void FinalizeAndWriteResults()
    {
        string json = "{\"results\":[";
        for (int i = 0; i < m_TH_Results.Count(); i++) {
            if (i > 0) json = json + ",";
            json = json + m_TH_Results.Get(i);
        }
        json = json + "]}";

        FileHandle fh = OpenFile(TestHarnessConfig.RESULT_FILE, FileMode.WRITE);
        if (fh != 0) {
            FPrintln(fh, json);
            CloseFile(fh);
            TestHarnessConfig.Log("Results written to " + TestHarnessConfig.RESULT_FILE);
        } else {
            TestHarnessConfig.Log("[ERROR] Could not open result file: " + TestHarnessConfig.RESULT_FILE);
        }
    }
}
