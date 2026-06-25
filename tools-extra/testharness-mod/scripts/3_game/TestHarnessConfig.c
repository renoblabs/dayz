// TestHarness config - scenario definitions + timing.
//
// Keep this small and declarative. Individual scenarios live in
// 5_mission/TestRunner.c. Adding a new scenario is an entry in
// SCENARIOS + a method on TestRunner.

class TestHarnessConfig {
    // Write scenario results here; modctl + test scripts read it back.
    static string RESULT_FILE = "$profile:testharness_results.json";

    // Delay (ms) after mission init before firing the first scenario.
    static int START_DELAY_MS = 5000;

    // Delay (ms) between sequential scenarios.
    static int INTER_SCENARIO_DELAY_MS = 3000;

    // Named scenarios to run in order. Methods on TestRunner must exist.
    static ref array<string> SCENARIOS = {
        "boss_spawn_then_despawn",
        "bosssignal_emit_event",
    };

    static void Log(string msg) {
        Print("[TestHarness] " + msg);
    }
}
