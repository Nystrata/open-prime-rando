import argparse
import os.path
from pathlib import Path

from retro_data_structures.asset_manager import IsoFileProvider
from retro_data_structures.formats import Strg
from retro_data_structures.game_check import Game
import retro_data_structures.exceptions

from open_prime_rando.patcher_editor import PatcherEditor

_CUSTOM_WORLD_NAMES = {
    Game.ECHOES: {
        0x69802220: "FrontEnd",
        0xA50A80CC: "M01_SidehopperStation",
        0xAE171602: "M02_Spires",
        0xE3B0C703: "M03_CrossfireChaos",
        0x233E42BE: "M04_Pipeline",
        0x406ADD7F: "M05_SpiderComplex",
        0x7E19ED26: "M06_ShootingGallery",
    }
}


def filter_name(s: str) -> str:
    result = s.replace("!", "").replace(" ", "_").replace("'", "").replace('"', "").upper()
    while result and not result[0].isalpha():
        result = result[1:]
    return result


def generate_template(items: dict[str, int], suffix: str) -> str:
    template = f"# Generated by {os.path.basename(__file__)}\n\n"
    template += "\n".join(
        f"{filter_name(key)}{suffix} = 0x{items[key]:08X}"
        for key in sorted(items)
    )
    template += "\n"

    template += "\n\nNAME_TO_ID = {\n"
    for name in sorted(items):
        template += f"    \"{name}\": 0x{items[name]:08X},\n"
    template += "}\n"

    return template


def create_asset_id_files(editor: PatcherEditor, output_path: Path):
    output_path.mkdir(parents=True, exist_ok=True)

    custom_world_names = _CUSTOM_WORLD_NAMES.get(editor.target_game, {})
    world_names = {}

    for value in editor.all_asset_ids():
        if editor.get_asset_type(value).lower() != "mlvl":
            continue

        mlvl = editor.get_mlvl(value)

        try:
            strg = editor.get_parsed_asset(mlvl.raw.world_name_id, type_hint=Strg)
            world_name = strg.raw.string_tables[0].strings[0].string
        except retro_data_structures.exceptions.UnknownAssetId:
            if value not in custom_world_names:
                print(f"Skipping MLVL {value}: no name found")
                continue
            world_name = custom_world_names[value]

        world_names[world_name] = value

        names = {}

        for area in mlvl.raw.areas:
            try:
                strg = editor.get_parsed_asset(area.area_name_id, type_hint=Strg)
                area_name = strg.raw.string_tables[0].strings[0].string
            except retro_data_structures.exceptions.UnknownAssetId:
                area_name = area.internal_area_name

            names[area_name] = area.area_mrea_id

        output_path.joinpath(f"{filter_name(world_name)}.py").write_text(generate_template(names, "_MREA"))

    output_path.joinpath("world.py").write_text(generate_template(world_names, "_MLVL"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", required=True, choices=["echoes"])
    parser.add_argument("--iso", required=True, type=Path,
                        help="Path to where the ISO.")
    args = parser.parse_args()

    create_asset_id_files(
        PatcherEditor(IsoFileProvider(args.iso), Game.ECHOES),
        Path(__file__).parents[1].joinpath("open_prime_rando", args.game, "asset_ids"),
    )


if __name__ == '__main__':
    main()
