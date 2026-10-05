"""Проверка полного пользовательского сценария на временных данных."""

import main
from storage import load_data


def test_menu_saves_entities_and_reloads_history(
    tmp_path, monkeypatch, capsys,
):
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
    assert len(data.rooms) == len(data.sensors) == 1
    assert len(data.readings) == 3
    assert data.reports[0].status == "ПРЕДУПРЕЖДЕНИЕ"
    assert data.readings[0].maximum == 20
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
    assert load_data(tmp_path).rooms == []


def test_all_menu_actions_with_restart(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    answers = iter([
        "2", "Архив", "2", "40", "2", "Серверная", "3", "25,5",
        "1", "3", "АРХ", "4", "5", "3", "6", "1", "0", "0",
        "7", "1", "8", "9", "10", "11", "12", "temperature", "10", "20",
        "7", "2", "13", "2", "6", "2", "2", "99", "0",
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr("monitoring.random.uniform", lambda low, high: low)
    monkeypatch.setattr("monitoring.random.randint", lambda *_: 2)
    main.main()
    data = load_data(tmp_path)
    output = capsys.readouterr().out
    assert "НЕТ ДАННЫХ" in output
    assert "Для активности введите 0 или 1" in output
    assert "Нет такого пункта меню" in output
    assert len(data.rooms) == 2
    assert len(data.reports) == 4
    assert len(data.readings) == 6
    assert not data.sensors[0].is_available()
    assert data.sensors[1].is_available()
    answers = iter(["9", "10", "13", "2", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    main.main()
    assert "Серверная" in capsys.readouterr().out
    assert load_data(tmp_path) == data
