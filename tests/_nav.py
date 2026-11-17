"""Test helper: open a habitat on the Assessment page (the Map page no longer has per-habitat 'open' cards)."""


def open_habitat(at, card_id: str):
    """`card_id` is a habitat key, or an old card id such as 'hab_esi_1a'. Goes to the Assessment page and selects the habitat
    there, without running an assessment."""
    key = card_id[4:] if card_id.startswith("hab_") else card_id
    key = {"esi_1a": "esi_1A", "esi_8a": "esi_8A"}.get(key, key)
    at.segmented_control(key="page").set_value("site").run()
    at.segmented_control(key="site_habitat").set_value(key).run()
    return at
