"""Типизированные коллекции объектов приложения."""

from dataclasses import dataclass, field

from models.metrics import Metric, default_metrics
from models.readings import Reading
from models.reports import Report
from models.rooms import Room
from models.sensors import Sensor


@dataclass
class ProjectData:
    """Контейнер состояния; deepcopy сохраняет общие ссылки внутри копии."""

    rooms: list[Room] = field(default_factory=list)
    sensors: list[Sensor] = field(default_factory=list)
    metrics: list[Metric] = field(default_factory=default_metrics)
    readings: list[Reading] = field(default_factory=list)
    reports: list[Report] = field(default_factory=list)
