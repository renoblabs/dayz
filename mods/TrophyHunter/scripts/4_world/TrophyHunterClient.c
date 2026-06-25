// ============================================================
// TrophyHunterClient - REST helper (load order 4_world, server only).
//
// Two operations:
//   Post(endpoint, bodyJson)          - fire-and-forget POST w/ shared secret
//   GetTopDamagerAlias(fullUrl, cb)   - async GET; TrophyAwarder is the callback
// ============================================================
class TrophyHunterClient {
    protected RestContext m_Rest;
    protected bool        m_Ready;

    // Strong refs to prevent callbacks being GC'd before they fire.
    // Matches BossSignal's pattern; bounded prune avoids unbounded growth.
    protected ref array<ref RestCallback> m_PendingCallbacks;
    protected static const int MAX_PENDING = 32;

    void TrophyHunterClient() {
        m_PendingCallbacks = new array<ref RestCallback>();
        m_Ready = false;
        if (GetGame().IsServer()) {
            RestApi api = GetRestApi();
            if (api) {
                m_Rest  = api.GetRestContext(TrophyHunterConfig.BACKEND_URL);
                m_Ready = (m_Rest != null);
            }
        }
        if (!m_Ready) {
            TrophyHunterConfig.Err("REST not available - trophies will not fire.");
            return;
        }
        // DayZ RestContext.SetHeader is value-only; sets only Content-Type.
        // Custom headers unsupported - auth/server-id go via query string.
        m_Rest.SetHeader("application/json");
    }

    bool IsReady() { return m_Ready; }

    protected string QueryAuth() {
        return "?secret=" + TrophyHunterConfig.SHARED_SECRET + "&server_id=" + TrophyHunterConfig.SERVER_ID;
    }

    void Post(string endpoint, string bodyJson) {
        if (!m_Ready) return;
        ref RestCallback cb = new TrophyHunterPostCB();
        m_PendingCallbacks.Insert(cb);
        PruneCallbacks();
        m_Rest.POST(cb, endpoint + QueryAuth(), bodyJson);
    }

    void GetTopDamagerAlias(string fullEndpoint, TrophyHunterCallback cb) {
        if (!m_Ready) { cb.OnTopDamagerFailed("client_not_ready"); return; }
        // fullEndpoint may already contain a query string (?skip_holders=...)
        string sep = "?";
        if (fullEndpoint.Contains("?")) sep = "&";
        string authed = fullEndpoint + sep + "secret=" + TrophyHunterConfig.SHARED_SECRET + "&server_id=" + TrophyHunterConfig.SERVER_ID;
        ref RestCallback getCb = new TrophyHunterGetCB(cb);
        m_PendingCallbacks.Insert(getCb);
        PruneCallbacks();
        m_Rest.GET(getCb, authed);
    }

    protected void PruneCallbacks() {
        if (m_PendingCallbacks.Count() > MAX_PENDING) {
            int excess = m_PendingCallbacks.Count() - MAX_PENDING;
            for (int i = 0; i < excess; i++) m_PendingCallbacks.Remove(0);
        }
    }
};

class TrophyHunterPostCB extends RestCallback {
    override void OnError(int errorCode) { TrophyHunterConfig.Warn("POST error "   + errorCode); }
    override void OnTimeout()            { TrophyHunterConfig.Warn("POST timeout"); }
    override void OnSuccess(string data, int dataSize) {}
}

class TrophyHunterGetCB extends RestCallback {
    protected ref TrophyHunterCallback m_UserCB;
    void TrophyHunterGetCB(TrophyHunterCallback cb) { m_UserCB = cb; }
    override void OnError(int errorCode) { if (m_UserCB) m_UserCB.OnTopDamagerFailed("http_error_" + errorCode); }
    override void OnTimeout()            { if (m_UserCB) m_UserCB.OnTopDamagerFailed("timeout"); }
    override void OnSuccess(string data, int dataSize) {
        if (m_UserCB) m_UserCB.OnTopDamagerSuccess(data);
    }
}

class TrophyHunterCallback {
    void OnTopDamagerSuccess(string jsonBody) {}
    void OnTopDamagerFailed(string reason)   {}
}
