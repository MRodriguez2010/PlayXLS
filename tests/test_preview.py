import playxls.video as video_module
from playxls.preview import PreviewPool


def test_preview_pool_prefers_configured_mpv_controller_factory():
    pool = PreviewPool(max_size=2)

    assert pool.mpv_factory is video_module.preferred_mpv_controller


def test_preview_pool_starts_muted_looping_preview():
    factory = FakeMpvFactory()
    pool = PreviewPool(max_size=2, mpv_factory=factory)

    controller = pool.start("one.mp4", window_id=101, muted=True)

    assert controller is factory.controllers[0]
    assert controller.loaded == ("one.mp4", False, True, 0)
    assert controller.paused is False


def test_preview_pool_reuses_warm_entry_for_same_source_and_window():
    factory = FakeMpvFactory()
    pool = PreviewPool(max_size=2, mpv_factory=factory)

    first = pool.start("one.mp4", window_id=101, muted=True)
    pool.pause("one.mp4")
    second = pool.start("one.mp4", window_id=101, muted=False)

    assert second is first
    assert len(factory.controllers) == 1
    assert second.paused is False
    assert second.volumes[-1] == 60


def test_preview_pool_reloads_when_warm_entry_has_different_window():
    factory = FakeMpvFactory()
    pool = PreviewPool(max_size=2, mpv_factory=factory)

    old = pool.start("one.mp4", window_id=101, muted=True)
    new = pool.start("one.mp4", window_id=202, muted=True)

    assert new is not old
    assert old.stopped is True
    assert len(factory.controllers) == 2


def test_preview_pool_evicts_least_recently_used_entry():
    factory = FakeMpvFactory()
    pool = PreviewPool(max_size=2, mpv_factory=factory)

    first = pool.start("one.mp4", window_id=101, muted=True)
    pool.start("two.mp4", window_id=102, muted=True)
    pool.start("three.mp4", window_id=103, muted=True)

    assert first.stopped is True
    assert pool.sources() == ["two.mp4", "three.mp4"]


def test_preview_pool_can_be_disabled():
    factory = FakeMpvFactory()
    pool = PreviewPool(max_size=0, mpv_factory=factory)

    assert pool.start("one.mp4", window_id=101, muted=True) is None
    assert factory.controllers == []


class FakeMpvFactory:
    def __init__(self) -> None:
        self.controllers: list[FakeMpv] = []

    def __call__(self, *, window_id: int | None = None):
        controller = FakeMpv(window_id)
        self.controllers.append(controller)
        return controller


class FakeMpv:
    available = True

    def __init__(self, window_id: int | None) -> None:
        self.window_id = window_id
        self.loaded = None
        self.paused = None
        self.volumes: list[float] = []
        self.stopped = False

    def load(self, source: str, *, paused: bool = False, loop: bool = False, volume: int = 60, audio_normalize: bool = False) -> bool:
        self.loaded = (source, paused, loop, volume)
        self.paused = paused
        self.volumes.append(volume)
        return True

    def set_pause(self, paused: bool) -> None:
        self.paused = paused

    def set_volume(self, volume: float) -> None:
        self.volumes.append(int(volume * 100))

    def stop(self) -> None:
        self.stopped = True
