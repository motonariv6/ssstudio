"""Per-page panorama settings and shared integer screen geometry."""
from dataclasses import dataclass, asdict


@dataclass
class PanoramaConfig:
    enabled: bool = False
    screen_count: int = 1
    direction: str = "horizontal"

    def validate(self):
        if self.direction != "horizontal":
            raise ValueError("Only horizontal panorama is supported")
        allowed = (2, 3, 4) if self.enabled else (1, 2, 3, 4)
        if type(self.screen_count) is not int or self.screen_count not in allowed:
            raise ValueError("Panorama requires 2, 3 or 4 screens")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        config = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        config.validate()
        return config


@dataclass(frozen=True)
class WorkspaceGeometry:
    screen_width: int
    screen_height: int
    screen_count: int

    @property
    def width(self):
        return self.screen_width * self.screen_count

    @property
    def height(self):
        return self.screen_height

    @property
    def boundaries(self):
        return tuple(i * self.screen_width for i in range(1, self.screen_count))

    @property
    def screen_rectangles(self):
        return tuple((i * self.screen_width, 0, (i + 1) * self.screen_width, self.height)
                     for i in range(self.screen_count))

    @property
    def slice_boxes(self):
        return self.screen_rectangles


def get_workspace_geometry(project, page):
    page.panorama.validate()
    return WorkspaceGeometry(project.canvas_width, project.canvas_height,
                             page.panorama.screen_count if page.panorama.enabled else 1)
