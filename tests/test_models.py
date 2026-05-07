from playxls.models import AppState, CellContent, SessionState


def test_app_state_applies_saved_session_and_preserves_capacity():
    state = AppState()
    session = SessionState(
        layout_id="1+2",
        cell_content=[CellContent.video("v1"), CellContent.browser("https://youtube.com", "YouTube")],
        master_volume=0.3,
        muted=True,
    )

    state.apply_session(session)

    assert state.layout_id == "1+2"
    assert state.cell_content[0] == CellContent.video("v1")
    assert state.cell_content[1] == CellContent.browser("https://youtube.com", "YouTube")
    assert len(state.cell_content) >= 20
    assert state.master_volume == 0.3
    assert state.muted is True


def test_app_state_preserves_main_splitter_sizes_through_session():
    state = AppState()
    session = SessionState(main_splitter_sizes=[260, 1020])

    state.apply_session(session)

    assert state.main_splitter_sizes == [260, 1020]
    assert state.to_session().main_splitter_sizes == [260, 1020]
