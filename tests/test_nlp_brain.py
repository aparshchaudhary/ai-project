import pytest
from backend.services.nlp_service import nlp_service


def test_app_open_and_close_hindi_english():
    # 1. Hindi suffix open
    res1 = nlp_service.parse_intent("chrome open karo")
    assert res1.intent == "open_application"
    assert res1.entities.get("application") == "chrome"

    res2 = nlp_service.parse_intent("whatsapp open karo")
    assert res2.intent == "open_application"
    assert res2.entities.get("application") == "whatsapp"

    res3 = nlp_service.parse_intent("notepad kholo")
    assert res3.intent == "open_application"
    assert res3.entities.get("application") == "notepad"

    # 2. Hindi suffix close
    res4 = nlp_service.parse_intent("chrome band karo")
    assert res4.intent == "close_application"
    assert res4.entities.get("application") == "chrome"

    res5 = nlp_service.parse_intent("whatsapp band karo")
    assert res5.intent == "close_application"
    assert res5.entities.get("application") == "whatsapp"

    res6 = nlp_service.parse_intent("notepad close karo")
    assert res6.intent == "close_application"
    assert res6.entities.get("application") == "notepad"


def test_time_date_day_hindi_english():
    # Time
    assert nlp_service.parse_intent("time batao").intent == "get_time"
    assert nlp_service.parse_intent("samay batao").intent == "get_time"
    assert nlp_service.parse_intent("what is the time").intent == "get_time"
    assert nlp_service.parse_intent("kitne baje").intent == "get_time"

    # Date
    assert nlp_service.parse_intent("tarikh batao").intent == "get_date"
    assert nlp_service.parse_intent("aaj ki tarikh").intent == "get_date"
    assert nlp_service.parse_intent("tell me today's date").intent == "get_date"

    # Day
    assert nlp_service.parse_intent("aaj kya din hai").intent == "get_date"
    assert nlp_service.parse_intent("what day is today").intent == "get_date"


def test_music_and_volume_hindi_english():
    # Music
    assert nlp_service.parse_intent("gaana bajao").intent == "play_music"
    assert nlp_service.parse_intent("gaana play karo").intent == "play_music"
    assert nlp_service.parse_intent("music chalao").intent == "play_music"
    assert nlp_service.parse_intent("gaana roko").intent == "pause_music"
    assert nlp_service.parse_intent("music band karo").intent == "pause_music"

    # Volume
    vol_up = nlp_service.parse_intent("volume badhao")
    assert vol_up.intent == "volume_control"
    assert vol_up.entities.get("action") == "up"

    vol_down = nlp_service.parse_intent("awaz kam karo")
    assert vol_down.intent == "volume_control"
    assert vol_down.entities.get("action") == "down"

    mute = nlp_service.parse_intent("mute karo")
    assert mute.intent == "volume_control"
    assert mute.entities.get("action") == "mute"


def test_search_and_files_hindi():
    # YouTube search
    yt = nlp_service.parse_intent("youtube par python search karo")
    assert yt.intent == "search_web"
    assert yt.entities.get("engine") == "youtube"
    assert "python" in yt.entities.get("query", "").lower()

    # Google search
    g = nlp_service.parse_intent("google par search karo ai news")
    assert g.intent == "search_web"
    assert g.entities.get("engine") == "google"
    assert "ai news" in g.entities.get("query", "").lower()

    # Files & Folders
    folder = nlp_service.parse_intent("folder banao College Projects")
    assert folder.intent == "create_folder"
    assert "College" in folder.entities.get("folder_name", "")

    file_res = nlp_service.parse_intent("file banao notes.txt")
    assert file_res.intent == "create_file"
    assert "notes.txt" in file_res.entities.get("file_name", "")


def test_conversational_brain_greetings_and_knowledge():
    # Greetings
    h = nlp_service.parse_intent("hello")
    assert h.intent == "conversation"
    assert "Aura" in h.response_text or "Hello" in h.response_text

    namaste = nlp_service.parse_intent("namaste")
    assert namaste.intent == "conversation"
    assert "Namaste" in namaste.response_text

    status = nlp_service.parse_intent("kaise ho")
    assert status.intent == "conversation"
    assert "badhiya" in status.response_text.lower() or "doing great" in status.response_text.lower()

    # Identity
    who = nlp_service.parse_intent("who are you")
    assert who.intent == "conversation"
    assert "Aura" in who.response_text

    # Tech knowledge
    ai_res = nlp_service.parse_intent("what is ai")
    assert ai_res.intent == "conversation"
    assert "intelligence" in ai_res.response_text.lower()
