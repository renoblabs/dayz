modded class PlayerBase
{
    private string m_hiveCharacterID = "";

    void SetHiveCharacterID(string id)
    {
        m_hiveCharacterID = id;
    }

    string GetHiveCharacterID()
    {
        return m_hiveCharacterID;
    }

    bool HasHiveCharacterID()
    {
        return m_hiveCharacterID != "";
    }
};
