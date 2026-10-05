"""Показатель и независимый снимок анализа значения."""

from dataclasses import dataclass

from models.validation import require_number, require_text


@dataclass(frozen=True)
class MetricAnalysis:
    """Неизменяемый результат анализа с историческими границами."""

    value: float
    minimum: float
    maximum: float
    normal: bool
    position: str
    deviation: float

    def __post_init__(self) -> None:
        for value in (self.value, self.minimum, self.maximum, self.deviation):
            require_number(value, "анализ показателя")
        if self.minimum > self.maximum:
            raise ValueError("Минимальная граница больше максимальной.")
        if self.value < self.minimum:
            position, deviation = "below", self.minimum - self.value
        elif self.value > self.maximum:
            position, deviation = "above", self.value - self.maximum
        else:
            position = "normal"
            deviation = abs(self.value - (self.minimum + self.maximum) / 2)
        if (type(self.normal) is not bool
                or self.normal != (position == "normal")
                or self.position != position
                or self.deviation != round(deviation, 2)):
            raise ValueError("Некорректный результат анализа показателя.")


def analyze_metric(value: float, minimum: float,
                   maximum: float) -> MetricAnalysis:
    """Чистый расчёт, используемый и для текущих, и для старых норм."""
    for number in (value, minimum, maximum):
        require_number(number, "показание или граница")
    if minimum > maximum:
        raise ValueError("Минимальная граница больше максимальной.")
    if value < minimum:
        position, deviation = "below", minimum - value
    elif value > maximum:
        position, deviation = "above", value - maximum
    else:
        position = "normal"
        deviation = abs(value - (minimum + maximum) / 2)
    return MetricAnalysis(value, minimum, maximum, position == "normal",
                          position, round(deviation, 2))


@dataclass
class Metric:
    """Справочник величин с изменяемыми нормами будущих проверок."""

    id: str
    name: str
    unit: str
    minimum: float
    maximum: float

    def __init__(self, metric_id: str, name: str, unit: str,
                 minimum: float, maximum: float) -> None:
        self.id = metric_id
        self.name = name
        self.unit = unit
        self.minimum = minimum
        self.maximum = maximum
        self.validate()

    def _validate_limits(self, minimum: float, maximum: float) -> None:
        require_number(minimum, "нижняя граница")
        require_number(maximum, "верхняя граница")
        if minimum > maximum:
            raise ValueError("Минимальная граница больше максимальной.")
        if self.id == "leak" and (minimum != 0 or maximum != 0):
            raise ValueError("Для протечки нормой всегда является 0.")

    def validate(self) -> None:
        for value in (self.id, self.name, self.unit):
            require_text(value, "показатель")
        self._validate_limits(self.minimum, self.maximum)

    def update_limits(self, minimum: float, maximum: float) -> None:
        self._validate_limits(minimum, maximum)
        self.minimum = minimum
        self.maximum = maximum

    def analyze(self, value: float) -> MetricAnalysis:
        return analyze_metric(value, self.minimum, self.maximum)

    def __str__(self) -> str:
        return (f"{self.id}: {self.name} | "
                f"{self.minimum}–{self.maximum} {self.unit}")


def default_metrics() -> list[Metric]:
    """Учебные пороги; каждый вызов создаёт независимые объекты."""
    return [Metric("temperature", "Температура", "°C", 18.0, 24.0),
            Metric("humidity", "Влажность", "%", 40.0, 60.0),
            Metric("leak", "Протечка", "0/1", 0.0, 0.0)]


def get_metric(metrics: list[Metric], metric_id: str) -> Metric:
    for metric in metrics:
        if metric.id == metric_id:
            return metric
    raise ValueError(f"Показатель {metric_id} не найден.")
