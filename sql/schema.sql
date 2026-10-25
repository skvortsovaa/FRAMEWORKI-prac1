-- SmartSpace Monitor: самостоятельная база предметной области ПР7.
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    floor INTEGER NOT NULL,
    area REAL NOT NULL CHECK (area > 0)
);
CREATE TABLE IF NOT EXISTS sensors (
    id TEXT PRIMARY KEY NOT NULL,
    room_id INTEGER NOT NULL UNIQUE REFERENCES rooms(id),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    battery INTEGER NOT NULL DEFAULT 100 CHECK (battery BETWEEN 0 AND 100)
);
CREATE TABLE IF NOT EXISTS metrics (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    minimum REAL NOT NULL,
    maximum REAL NOT NULL,
    CHECK (minimum <= maximum)
);
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY NOT NULL,
    room_id INTEGER NOT NULL REFERENCES rooms(id),
    room_name TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    sensor_active INTEGER NOT NULL CHECK (sensor_active IN (0, 1)),
    battery INTEGER NOT NULL CHECK (battery BETWEEN 0 AND 100),
    temperature_value REAL,
    temperature_minimum REAL,
    temperature_maximum REAL,
    temperature_normal INTEGER CHECK (temperature_normal IN (0, 1)),
    humidity_value REAL,
    humidity_minimum REAL,
    humidity_maximum REAL,
    humidity_normal INTEGER CHECK (humidity_normal IN (0, 1)),
    leak_detected INTEGER CHECK (leak_detected IN (0, 1)),
    status TEXT NOT NULL CHECK (status IN
        ('НОРМА', 'ПРЕДУПРЕЖДЕНИЕ', 'АВАРИЯ', 'НЕТ ДАННЫХ')),
    CHECK ((sensor_active = 1 AND battery > 0
        AND temperature_value IS NOT NULL
        AND temperature_minimum IS NOT NULL
        AND temperature_maximum IS NOT NULL
        AND temperature_normal IS NOT NULL
        AND humidity_value IS NOT NULL AND humidity_minimum IS NOT NULL
        AND humidity_maximum IS NOT NULL AND humidity_normal IS NOT NULL
        AND leak_detected IS NOT NULL AND status <> 'НЕТ ДАННЫХ')
        OR ((sensor_active = 0 OR battery = 0)
        AND temperature_value IS NULL AND temperature_minimum IS NULL
        AND temperature_maximum IS NULL AND temperature_normal IS NULL
        AND humidity_value IS NULL AND humidity_minimum IS NULL
        AND humidity_maximum IS NULL AND humidity_normal IS NULL
        AND leak_detected IS NULL AND status = 'НЕТ ДАННЫХ'))
);
CREATE TABLE IF NOT EXISTS readings (
    id TEXT PRIMARY KEY NOT NULL,
    sensor_id TEXT NOT NULL REFERENCES sensors(id),
    metric_id TEXT NOT NULL REFERENCES metrics(id),
    report_id TEXT NOT NULL REFERENCES reports(id),
    measured_at TEXT NOT NULL,
    value REAL NOT NULL,
    minimum REAL NOT NULL,
    maximum REAL NOT NULL,
    status TEXT NOT NULL CHECK (status IN
        ('НОРМА', 'ПРЕДУПРЕЖДЕНИЕ', 'АВАРИЯ')),
    CHECK (minimum <= maximum),
    UNIQUE (report_id, metric_id)
);
CREATE INDEX IF NOT EXISTS reports_room_date ON reports(room_id, checked_at);
CREATE INDEX IF NOT EXISTS readings_measured_at ON readings(measured_at);
