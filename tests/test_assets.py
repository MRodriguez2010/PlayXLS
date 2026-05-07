from playxls.assets import app_icon_path, title_mark_path


def test_logo_pack_assets_are_discovered():
    assert app_icon_path().name == "playxls-icon-256.png"
    assert app_icon_path().exists()
    assert title_mark_path().name == "playxls-mark-primary.svg"
    assert title_mark_path().exists()
