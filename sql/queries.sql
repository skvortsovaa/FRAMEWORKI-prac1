-- name: rooms_list
-- 01 SELECT список помещений — /rooms/
SELECT id, name, floor, area FROM rooms ORDER BY id;

-- name: metrics_list
-- 02 SELECT справочник показателей — /reports/readings/
SELECT id, name, unit, minimum, maximum FROM metrics ORDER BY id;

-- name: rooms_by_area
-- 03 WHERE площадь не меньше порога — /rooms/?min_area=30
SELECT id, name, floor, area FROM rooms WHERE area >= ? ORDER BY area, id;

-- name: available_sensors
-- 04 WHERE доступные датчики — /sensors/?available=1
SELECT s.id, s.room_id, r.name AS room_name, s.active, s.battery,
       (s.active = 1 AND s.battery > 0) AS available
FROM sensors AS s JOIN rooms AS r ON r.id = s.room_id
WHERE s.active = 1 AND s.battery > 0 ORDER BY s.id;

-- name: sensors_with_rooms
-- 05 JOIN датчики с помещениями — /sensors/
SELECT s.id, s.room_id, r.name AS room_name, s.active, s.battery,
       (s.active = 1 AND s.battery > 0) AS available
FROM sensors AS s JOIN rooms AS r ON r.id = s.room_id ORDER BY s.id;

-- name: reports_with_rooms
-- 06 JOIN история и текущие помещения — /reports/
SELECT p.*, r.name AS current_room_name
FROM reports AS p JOIN rooms AS r ON r.id = p.room_id
ORDER BY p.checked_at DESC, p.id;

-- name: reports_filtered
-- 07 WHERE дата и статус — /reports/?date=2026-09-21&status=ПРЕДУПРЕЖДЕНИЕ
SELECT p.*, r.name AS current_room_name
FROM reports AS p JOIN rooms AS r ON r.id = p.room_id
WHERE (? = '' OR substr(p.checked_at, 1, 10) = ?)
  AND (? = '' OR p.status = ?)
ORDER BY p.checked_at DESC, p.id;

-- name: rooms_without_reports
-- 08 NOT EXISTS помещения без проверок на дату — /rooms/uninspected/
SELECT r.id, r.name, r.floor, r.area FROM rooms AS r
WHERE NOT EXISTS (
    SELECT 1 FROM reports AS p
    WHERE p.room_id = r.id AND substr(p.checked_at, 1, 10) = ?
) ORDER BY r.id;

-- name: room_count
-- 09 COUNT число помещений — /reports/statistics/
SELECT COUNT(*) AS total FROM rooms;

-- name: report_totals
-- 10 агрегаты истории — /reports/statistics/
SELECT COUNT(*) AS total,
       COALESCE(SUM(status = 'АВАРИЯ'), 0) AS alarms,
       COALESCE(SUM(status = 'НЕТ ДАННЫХ'), 0) AS no_data
FROM reports;

-- name: room_report_counts
-- 11 GROUP BY включая нулевые группы — /reports/statistics/
SELECT r.id, r.name AS room_name, COUNT(p.id) AS reports_count
FROM rooms AS r LEFT JOIN reports AS p ON p.room_id = r.id
GROUP BY r.id, r.name ORDER BY reports_count DESC, r.id;

-- name: status_counts
-- 12 GROUP BY по статусам — /reports/statistics/
SELECT status, COUNT(*) AS reports_count FROM reports
GROUP BY status ORDER BY reports_count DESC, status;

-- name: rooms_above_count
-- 13 HAVING групповой порог — /reports/statistics/?min_count=0
SELECT r.id, r.name AS room_name, COUNT(p.id) AS reports_count
FROM rooms AS r LEFT JOIN reports AS p ON p.room_id = r.id
GROUP BY r.id, r.name HAVING COUNT(p.id) > ?
ORDER BY reports_count DESC, r.id;

-- name: readings_list
-- 14 JOIN ORDER BY LIMIT OFFSET — /reports/readings/?limit=10&offset=0
SELECT v.id, v.report_id, v.measured_at, v.value, v.minimum,
       v.maximum, v.status, s.id AS sensor_id, r.name AS room_name,
       m.name AS metric_name, m.unit
FROM readings AS v
JOIN sensors AS s ON s.id = v.sensor_id
JOIN rooms AS r ON r.id = s.room_id
JOIN metrics AS m ON m.id = v.metric_id
ORDER BY v.measured_at DESC, v.id LIMIT ? OFFSET ?;

-- name: room_by_id
-- 15 параметризованный ID — /rooms/<id>/
SELECT id, name, floor, area FROM rooms WHERE id = ?;

-- name: sensor_by_room
-- 16 связанный датчик — /rooms/<id>/
SELECT id, room_id, active, battery,
       (active = 1 AND battery > 0) AS available
FROM sensors WHERE room_id = ?;

-- name: report_by_id
-- 17 снимок отчёта — /reports/<id>/
SELECT * FROM reports WHERE id = ?;

-- name: room_search
-- 18 поиск ID и площади — /rooms/?room_id=1&min_area=20
SELECT id, name, floor, area FROM rooms
WHERE id = ? AND area >= ? ORDER BY id;

-- name: metric_statistics
-- 19 MIN MAX AVG GROUP BY — /reports/statistics/
SELECT m.name AS metric_name, m.unit, COUNT(v.id) AS readings_count,
       MIN(v.value) AS minimum_value, MAX(v.value) AS maximum_value,
       AVG(v.value) AS average_value
FROM metrics AS m LEFT JOIN readings AS v ON v.metric_id = m.id
GROUP BY m.id, m.name, m.unit ORDER BY m.id;
