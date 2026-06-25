// ============================================================
// BossSignalClient - HTTP client wrapping Enforce's RestContext
// Load order : 4_world  (server-side only - GetRestApi() is server-only)
//
// CRITICAL DEVLOG ITEMS:
//
// DEVLOG-005: GetRestApi() availability
//   Confirmed server-side via Bohemia wiki + HiveApiMod source.
//   Do NOT call on client - gate with GetGame().IsServer().
//
// DEVLOG-006: RestContext.POST() exact signature
//   Expected: ctx.POST(RestCallback callback, string path, string body)
//   Validate by running against local test server on Day 1 and
//   checking RPT log for "[RestContext] POST ..." confirmation line.
//
// DEVLOG-007: RestCallback GC behaviour
//   The DayZ engine may or may not retain a ref to the callback
//   internally after .POST() is called. To be safe, m_PendingCallbacks
//   keeps strong refs until Tick() prunes them after a safe window.
//   If the engine crashes or panics, try disabling the prune and keeping
//   all callbacks alive until server restart.
//
// DEVLOG-008: RestContext header API
//   Expected: ctx.SetHeader("Key: Value")  (colon-separated, one string)
//   Alternative seen in some mods: ctx.AddHeader(key, value)
//   Test on first play - wrong header format causes silent auth failures.
// ============================================================


// ?? HTTP response callback ???????????????????????????????????
class BossSignalCallback : RestCallback {
    private string m_Endpoint;
    private string m_EventType;
    private float  m_SentAt;

    void BossSignalCallback(string endpoint, string eventType) {
        m_Endpoint  = endpoint;
        m_EventType = eventType;
        m_SentAt    = GetGame().GetTime();
    }

    override void OnSuccess(string data, int dataSize) {
        BossSignalConfig.Trace("http_ok " + m_EventType + " " + dataSize + "b");
        BossSignalConfig.Log("OK  " + m_EventType + " -> " + m_Endpoint + " (" + dataSize + "b back, " + Math.Round((GetGame().GetTime() - m_SentAt) * 1000) + "ms)");
    }

    override void OnError(int errorCode) {
        BossSignalConfig.Trace("http_err " + m_EventType + " code=" + errorCode);
        BossSignalConfig.Err("FAIL " + m_EventType + " -> " + m_Endpoint + " code=" + errorCode);
    }

    override void OnTimeout() {
        BossSignalConfig.Trace("http_timeout " + m_EventType);
        BossSignalConfig.Warn("TIMEOUT " + m_EventType + " -> " + m_Endpoint);
    }
};


// ?? HTTP client ??????????????????????????????????????????????
class BossSignalClient {
    protected RestContext             m_Ctx;
    protected bool                    m_Ready;

    // Strong refs to prevent callbacks being GC'd before they fire
    // DEVLOG-007
    protected ref array<ref BossSignalCallback> m_PendingCallbacks;
    protected static const int MAX_PENDING = 32;

    // ?? Constructor ??????????????????????????????????????????
    void BossSignalClient() {
        m_PendingCallbacks = new array<ref BossSignalCallback>();
        m_Ready = false;

        if (!GetGame().IsServer()) {
            BossSignalConfig.Err("BossSignalClient instantiated on client - this is a bug.");
            return;
        }

        // DEVLOG-006: GetRestApi().GetRestContext(baseUrl)
        m_Ctx = GetRestApi().GetRestContext(BossSignalConfig.BACKEND_URL);
        if (!m_Ctx) {
            BossSignalConfig.Err("GetRestContext returned null - check BACKEND_URL format.");
            return;
        }

        // DEVLOG-008 RESOLVED: DayZ RestContext.SetHeader(value) sets ONLY
        // the Content-Type header (name is hardcoded by engine). Passing
        // "Key: Value" produces a malformed header. Custom headers are
        // not supported via this API.
        //   -> Content-Type via SetHeader
        //   -> Auth/server-id via URL query params or JSON body instead
        m_Ctx.SetHeader("application/json");

        m_Ready = true;
        BossSignalConfig.Log("HTTP client ready -> " + BossSignalConfig.BACKEND_URL);
    }

    // ?? POST a JSON payload ???????????????????????????????????
    // DayZ RestContext only supports Content-Type via SetHeader - custom
    // headers don't work. So we pass auth/server-id via query string.
    void Post(string endpoint, string eventType, string jsonBody) {
        if (!m_Ready || !m_Ctx) {
            BossSignalConfig.Warn("Dropping event '" + eventType + "' - client not ready.");
            return;
        }

        ref BossSignalCallback cb = new BossSignalCallback(endpoint, eventType);
        m_PendingCallbacks.Insert(cb);

        string fullPath = endpoint + "?secret=" + BossSignalConfig.SHARED_SECRET + "&server_id=" + BossSignalConfig.SERVER_ID + "&version=" + BossSignalConfig.VERSION;
        BossSignalConfig.Trace("http_post " + eventType + " path=" + fullPath.Substring(0, Math.Min(60, fullPath.Length())));
        m_Ctx.POST(cb, fullPath, jsonBody);
    }

    // ?? Periodic maintenance - call from OnUpdate ?????????????
    // Prunes the pending-callback list after a safe window.
    // Assumption: HTTP round-trips complete within ~5 seconds.
    // If a local backend isn't responding, TIMEOUT fires after engine timeout.
    void Tick() {
        // Keep last MAX_PENDING. Everything before that has fired (or timed out).
        if (m_PendingCallbacks.Count() > MAX_PENDING) {
            int excess = m_PendingCallbacks.Count() - MAX_PENDING;
            for (int i = 0; i < excess; i++) {
                m_PendingCallbacks.Remove(0);
            }
        }
    }

    bool IsReady() { return m_Ready; }
};
