"""Проверка полного пользовательского сценария на временных данных."""

import main
from storage import load_data


def test_menu_saves_entities_and_reloads_history(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    answers = iter([
        "2", "Тестовая комната", "3", "25,5",
        "12", "temperature", "10", "20",
        "7", "1", "10", "11", "13", "1", "0",
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    values = iter([21, 50])
    monkeypatch.setattr("monitoring.random.uniform", lambda *_: next(values))
    monkeypatch.setattr("monitoring.random.randint", lambda *_: 2)
    main.main()
    data = load_data(tmp_path)
    assert len(data["rooms"]) == len(data["sensors"]) == 1
    assert len(data["readings"]) == 3
    assert data["reports"][0]["status"] == "ПРЕДУПРЕЖДЕНИЕ"
    assert data["readings"][0]["maximum"] == 20
    output = capsys.readouterr().out
    assert "Действие не сохранено" not in output
    assert "SENS-001" in output
    answers = iter(["9", "13", "1", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    main.main()
    assert "Тестовая комната" in capsys.readouterr().out
    assert load_data(tmp_path) == data


def test_menu_keeps_memory_after_failed_save(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    answers = iter(["2", "Не сохранено", "1", "20", "1", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    def fail(*args):
        raise OSError("Нет доступа")

    monkeypatch.setattr(main, "save_data", fail)
    main.main()
    output = capsys.readouterr().out
    assert "Действие не сохранено" in output
    assert "Помещений не найдено" in output
    assert load_data(tmp_path)["rooms"] == []
