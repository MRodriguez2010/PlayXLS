from playxls.layout import (
    LayoutNode,
    collect_cells,
    count_cells,
    layout_from_dict,
    layout_to_dict,
    preset_layouts,
    remove_leaf_at,
    set_ratio_at,
    split_leaf_at,
)


def test_required_presets_have_expected_cell_counts():
    presets = {layout.id: layout for layout in preset_layouts()}

    assert count_cells(presets["1x1"].tree) == 1
    assert count_cells(presets["1x2"].tree) == 2
    assert count_cells(presets["1x3"].tree) == 3
    assert count_cells(presets["2x2"].tree) == 4
    assert count_cells(presets["3x3"].tree) == 9
    assert count_cells(presets["1+2"].tree) == 3


def test_one_plus_two_stack_geometry_matches_prompt():
    tree = {layout.id: layout for layout in preset_layouts()}["1+2"].tree
    cells = collect_cells(tree)

    assert cells[0].as_tuple() == (0.0, 0.0, 60.0, 100.0)
    assert cells[1].as_tuple() == (60.0, 0.0, 40.0, 50.0)
    assert cells[2].as_tuple() == (60.0, 50.0, 40.0, 50.0)


def test_split_remove_and_ratio_updates_are_immutable():
    original = LayoutNode.leaf()
    split = split_leaf_at(original, [], "v")

    assert count_cells(original) == 1
    assert count_cells(split) == 2

    adjusted = set_ratio_at(split, [], 1.2)
    cells = collect_cells(adjusted)
    assert cells[0].w == 90.0
    assert cells[1].w == 10.0

    removed = remove_leaf_at(adjusted, ["a"])
    assert count_cells(removed) == 1
    assert adjusted.kind == "split"


def test_layout_serialization_round_trips_losslessly():
    tree = split_leaf_at(LayoutNode.leaf(), [], "h")
    tree = split_leaf_at(tree, ["a"], "v")
    tree = set_ratio_at(tree, ["a"], 0.33)

    encoded = layout_to_dict(tree)
    decoded = layout_from_dict(encoded)

    assert layout_to_dict(decoded) == encoded
    assert [cell.as_tuple() for cell in collect_cells(decoded)] == [
        (0.0, 0.0, 33.0, 50.0),
        (33.0, 0.0, 67.0, 50.0),
        (0.0, 50.0, 100.0, 50.0),
    ]
