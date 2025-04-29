"""
This is a simple API that takes a list of games and returns a list of matches.

The list of games is sent in the body of the request.

The console is sent in the url of the request.

The response is a json object with the console and the list of matches.
"""

import json
import logging
import re
import typing
import urllib.parse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, Response
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from thefuzz import fuzz, process

from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

MIN_MATCH_SCORE = 90


rom_mapping = {
    "PUAE": "Commodore - Amiga",
    "AMIGA": "Commodore - Amiga",
    "FBN": "FBNeo - Arcade Games",
    "CPC": "Amstrad - CPC",
    "ATARI": "Atari - 2600",
    "FIFTYTWOHUNDRED": "Atari - 5200",
    "LYNX": "Atari - Lynx",
    "COLECO": "Coleco - ColecoVision",
    "C64": "Commodore - 64",
    "COMMODORE": "Commodore - 64",
    "DOS": "DOS",
    "DOOM": "DOOM",
    "EASYRPG": "",
    "FDS": "Family Computer Disk System",
    "GW": "",
    "GB": "Nintendo - Game Boy",
    "GBA": "Nintendo - Game Boy Advance",
    "MGBA": "Nintendo - Game Boy Advance",
    "GBC": "Nintendo - Game Boy Color",
    "INTELLIVISION": "Mattel - Intellivision",
    "MEGADUCK": "",
    "MSX": "Microsoft - MSX",
    "NEOCD": "SNK - Neo Geo CD",
    "NGPC": "SNK - Neo Geo Pocket Color",
    "NEOGEO": "SNK - Neo Geo",
    "N64": "Nintendo - Nintendo 64",
    "NDS": "Nintendo - Nintendo DS",
    "FC": "Nintendo - Nintendo Entertainment System",
    "ODYSSEY": "Magnavox - Odyssey 2",
    "OPENBOR": "",
    "P8": "",
    "PICO": "",
    "PKM": "Nintendo - Pokemon Mini",
    "QUAKE": "Quake",
    "SCUMMVM": "ScummVM",
    "THIRTYTWOX": "Sega - 32X",
    "DC": "Sega - Dreamcast",
    "GG": "Sega - Game Gear",
    "MD": "Sega - Mega Drive - Genesis",
    "SMS": "Sega - Master System - Mark III",
    "SATURN": "Sega - Saturn",
    "PS": "Sony - PlayStation",
    "PSP": "Sony - PlayStation Portable",
    "SGB": "",
    "SGFX": "NEC - PC Engine SuperGrafx",
    "SFC": "Nintendo - Super Nintendo Entertainment System",
    "SUPA": "Nintendo - Super Nintendo Entertainment System",
    "TIC": "TIC-80",
    "FFMPEG": "",
    "PCE": "NEC - PC Engine - TurboGrafx 16",
    "VIC20": "Commodore - VIC-20",
    "VB": "Nintendo - Virtual Boy",
    "SUPERVISION": "Watara - Supervision",
    "WSC": "Bandai - WonderSwan Color",
    "X68000": "Sharp - X68000",
}

common_renames = {
    "Megaman": "Mega Man",
}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """
    Initialize the cache.
    """
    FastAPICache.init(InMemoryBackend())
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def handle_index():
    """
    Handle the index page.
    """
    return {"Hello": "World"}


class PrettyJSONResponse(Response):
    """
    A response that renders json with indents.
    """

    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        """
        Render the json with indents.
        """
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=4,
            separators=(", ", ": "),
        ).encode("utf-8")


@app.post("/matches/{console}/{image_type}")
async def handle_rom_list(console: str, image_type: str, request: Request):
    """
    Handle the rom list page.
    """
    body = await request.body()

    matches, games = await process_game_list(console, body, image_type)

    if request.headers.get("content-type") == "text/plain":
        output = [f"{game}\t{matches[game]}" for game in matches]
        return Response("\n".join(output), media_type="text/plain")

    return PrettyJSONResponse(
        {
            "data": {
                "console": console,
                "matches": matches,
            },
            "stats": {
                "total_games": len(games),
                "total_matches": len(matches.keys()),
            },
        }
    )


def scrub_game_name(game_name: str) -> str:
    """
    Scrub the game name.
    """
    game_name = re.sub(r"\.\w+$", "", game_name)

    # remove the contents inside of parenthesis or brackets
    game_name = re.sub(r"\s*\([^)]*\)", "", game_name)
    game_name = re.sub(r"\s*\[[^\]]*\]", "", game_name)

    for old_name, new_name in common_renames.items():
        game_name = game_name.replace(old_name, new_name)

    return game_name.strip()


# cache for 1 day
@cache(expire=60 * 60 * 24)
def get_games_from_libretro(base_url: str) -> dict[str, str]:
    """
    Get the games from the libretro api.
    """
    logger.info("getting games from libretro", extra={"base_url": base_url})
    response = requests.get(base_url, timeout=10)
    if response.status_code != 200:
        return {}

    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a")

    game_mapping = {
        scrub_game_name(link.text): link.get("href")
        for link in links
        if link.get("href").endswith(".png")
    }

    return game_mapping


async def process_game_list(
    console: str, body: bytes, image_type: str
) -> dict[str, str]:
    """
    Process the game list.
    """
    games = [game.strip() for game in body.decode("utf-8").split("\n") if game.strip()]
    games = [game for game in games if not game.startswith(".")]
    games = [game for game in games if game != "neogeo.zip"]

    mapped_console = rom_mapping.get(console, None)
    if not mapped_console:
        logger.warning("no mapped console found", extra={"console": console})
        return {}, {}

    image_folders = {
        "boxart": "Named_Boxarts",
        "snap": "Named_Snaps",
        "title": "Named_Titles",
    }
    image_folder = image_folders.get(image_type, None)
    if not image_folder:
        logger.warning("no image folder found", extra={"image_type": image_type})
        return {}, {}

    base_url = f"https://thumbnails.libretro.com/{mapped_console}/{image_folder}/"
    quoted_base_url = urllib.parse.quote(base_url, safe=":/")

    game_mapping = await get_games_from_libretro(base_url)
    if len(game_mapping) == 0:
        logger.warning("no games found", extra={"console": console})
        return {}, {}

    matches = {}

    fuzzers = [
        fuzz.ratio,
        fuzz.token_sort_ratio,
        fuzz.token_set_ratio,
        fuzz.partial_ratio,
        fuzz.partial_token_sort_ratio,
    ]

    exact_matches = []
    all_games = games.copy()
    for game in games:
        scrubbed_game = scrub_game_name(game)
        exact_match = game_mapping.get(scrubbed_game, None)
        if exact_match:
            matches[game] = f"{quoted_base_url}{exact_match}"
            del game_mapping[scrubbed_game]
            exact_matches.append(game)

    for exact_match in exact_matches:
        games.remove(exact_match)

    game_names = list(game_mapping.keys())
    for game in games:
        scrubbed_game = scrub_game_name(game)

        best_match = None
        for fuzzer in fuzzers:
            best_match = process.extractOne(scrubbed_game, game_names, scorer=fuzzer)

            if best_match[1] < MIN_MATCH_SCORE:
                logger.warning(
                    "score too low",
                    extra={
                        "game": game,
                        "scrubbed_game": scrubbed_game,
                        "score": best_match[1],
                        "best_match": best_match[0],
                    },
                )
                continue

            break

        if not best_match:
            logger.warning(
                "no match found",
                extra={
                    "game": game,
                    "scrubbed_game": scrubbed_game,
                },
            )
            continue

        if best_match[1] < MIN_MATCH_SCORE:
            logger.warning(
                "score too low, no match found",
                extra={
                    "game": game,
                    "scrubbed_game": scrubbed_game,
                    "score": best_match[1],
                    "best_match": best_match[0],
                },
            )
            continue

        image_name = game_mapping[best_match[0]]
        matches[game] = f"{quoted_base_url}{image_name}"

    return matches, all_games
