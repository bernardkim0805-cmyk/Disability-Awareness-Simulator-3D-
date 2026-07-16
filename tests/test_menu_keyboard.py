"""Headless checks for the menu's explicit keyboard command map."""

from types import SimpleNamespace

from simulator.menu import MainMenu


def _fake_menu():
    calls = []
    menu = SimpleNamespace(
        ui=SimpleNamespace(enabled=True),
        accept_input=True,
        select_disability=lambda key: calls.append(("experience", key)),
        select_scenario=lambda key: calls.append(("scenario", key)),
        open_lab=lambda: calls.append(("lab", None)),
        start_game=lambda: calls.append(("start", None)),
    )
    return menu, calls


def test_every_main_menu_action_has_an_explicit_key():
    menu, calls = _fake_menu()
    for key in "1234567":
        MainMenu.input(menu, key)
    for key in "890":
        MainMenu.input(menu, key)
    MainMenu.input(menu, "l")
    MainMenu.input(menu, "enter")

    assert [value for action, value in calls if action == "experience"] == [
        "none", "adhd", "schizophrenia", "wheelchair", "visual", "deaf", "dyslexia"
    ]
    assert [value for action, value in calls if action == "scenario"] == [
        "school", "train", "zombies"
    ]
    assert ("lab", None) in calls
    assert ("start", None) in calls


def test_menu_ignores_keys_while_an_overlay_owns_input():
    menu, calls = _fake_menu()
    menu.ui.enabled = False
    MainMenu.input(menu, "enter")
    assert calls == []
