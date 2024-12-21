import inquirer
from termcolor import colored
from time import sleep
import plyer
import os
import json
from alive_progress import alive_bar
import sys
from datetime import datetime
from typing import List, Tuple, Dict, Optional, Any, NamedTuple

from modules import *

# ----------------------------------------------------------------------
# CONFIGURATION VARIABLES AND SHARED STATE
# ----------------------------------------------------------------------

DEBUG = sys.gettrace() is not None
VERSION = "1.5.2"
OWD = os.getcwd()
PLATFORM = sys.platform
TEST_SETTINGS = NamedTuple(
    "TestSettings",
    [
        ("use_test_file", bool),
        ("test_small_file", bool),
        ("test_large_file", bool),
        ("test_very_large_file", bool),
        ("skip_site_check", bool),
    ],
)
TEST = TEST_SETTINGS(
    use_test_file=True,
    test_small_file=True,
    test_large_file=False,
    test_very_large_file=False,
    skip_site_check=True,
)

# ----------------------------------------------------------------------
# UTILITY FUNCTIONS
# ----------------------------------------------------------------------

def print_logo():
    version_color = "cyan" if not os.path.exists("outdated") else \
        "cyan,blink"
    version_for_logo = colored(f"v{VERSION}", version_color)
    logo = f"""{colored(f'''
    .88b  d88. db    db db             d888888b  .d88b. d8888b.
    88'YbdP`88 88    88 88             `~~88~~' .8P  Y8. 88  `8D
    88  88  88 88    88 88                88    88    88 88oobY'
    88  88  88 88    88 88      C8888D    88    88    88 88`8b
    88  88  88 88b  d88 88booo.           88    `8b  d8' 88 `88.
    YP  YP  YP ~Y8888P' Y88888P           YP     `Y88P'  88   YD
                                        {version_for_logo} | by \
{colored("Official-Husko", "yellow")}''', "red")}
    """
    print(logo)
    if DEBUG:
        print(f"{colored('Platform:', 'green')} {PLATFORM}")
        print("")

def set_window_title():
    if PLATFORM == "win32":
        os.system("cls")
        title = (
            f"Mul-Tor | v{VERSION} - Development Build"
            if DEBUG
            else f"Mul-Tor | v{VERSION}"
        )
        from ctypes import windll

        windll.kernel32.SetConsoleTitleW(title)
    print_logo()

def log_and_print_error(message: str, exception: str, extra: str = ""):
    error_msg = (
        f"{colored('Error:', 'red')} {message} Exception: "
        f"{colored(exception, 'red')}"
    )
    print(error_msg)
    Logger.log_event(message, extra)

# ----------------------------------------------------------------------
# DATA VALIDATION AND CONFIGURATION
# ----------------------------------------------------------------------

def load_configuration() -> dict:
    config = Config_Manager.Checker()
    if not config:
        print(
            colored(
                "Error: Could not load or create config file.", "red"
            )
        )
        exit(1)
    return config

def fetch_resources(config: dict) -> Tuple[List[str], List[str]]:
    proxies_enabled = config.get("useProxies", False)
    random_ua_enabled = config.get("randomUserAgent", False)

    proxy_list = []
    if proxies_enabled:
        print(colored("Fetching Fresh Proxies...", "yellow"), end="\r")
        proxy_list = ProxyScraper.Scraper()
        print(
            f"{colored(f'Fetched', 'green')} "
            f"{colored(len(proxy_list), 'yellow')} "
            f"{colored('Proxies.        ', 'green')}"
        )
        print("")

    ua_list = []
    if random_ua_enabled:
        ua_list = (
            UserAgentManager.Reader()
            if os.path.exists("user_agents.json")
            else UserAgentManager.Scraper()
        )
    else:
        ua_list = [f"mul-tor/{VERSION} (by Official Husko on GitHub)"]

    return proxy_list, ua_list

def check_for_updates(config: dict):
    check_for_updates_enabled = config.get("checkForUpdates", False)
    if check_for_updates_enabled:
        set_window_title()
        print(colored("Checking for Updates...", "yellow"), end="\r")
        AutoUpdate.Checker()
        set_window_title()

def check_availability(
    config: dict, proxy_list: list, ua_list: list
) -> list:
    available = Availability_Checker.Evaluate(
        config, proxy_list, ua_list
    )
    if DEBUG:
        print(f"Available sites: {available}")
    if not available:
        print(
            colored(
                "No sites are available. Please double check your "
                "config (and preset if used). If you think this is "
                "an error please report it on github.",
                "red",
            )
        )
        sleep(10)
        exit(0)
    return available

def setup_presets_directory():
    if not os.path.exists("presets"):
        os.mkdir("presets")
    if not os.path.exists(f"presets/readme.txt"):
        with open("presets\\readme.txt", "a") as readme:
            text = (
                "To create your own preset visit the wiki here: "
                "https://github.com/Official-Husko/mul-tor/wiki/"
                "Preset-Configuration"
            )
            readme.write(text)
        readme.close()

# ----------------------------------------------------------------------
# FILE SELECTION AND UPLOAD LOGIC
# ----------------------------------------------------------------------

def select_files() -> List[str]:
    if DEBUG and TEST.use_test_file:
        if TEST.test_small_file:
            return [f"{os.path.join(OWD, 'test.png')}"]
        elif TEST.test_large_file:
            return [f"{os.path.join(OWD, 'big_game.7z')}"]
        elif TEST.test_very_large_file:
            return [f"{os.path.join(OWD, 'very_big_game.7z')}"]
        else:
            log_and_print_error(
                "Test file config error.",
                "Please report this on github. Test_File_Error",
            )
            return []

    amount_question = [
        inquirer.List(
            "selection",
            message=colored(
                "What file/s do you want to upload?", "green"
            ),
            choices=["Single", "Multiple"],
        ),
    ]
    amount_answers = inquirer.prompt(amount_question)
    print("")

    files_list = []
    while not files_list:
        if amount_answers.get("selection") == "Single":
            files_list = plyer.filechooser.open_file()
        elif amount_answers.get("selection") == "Multiple":
            folder_path = plyer.filechooser.choose_dir()
            if folder_path:
                folder_path = folder_path[0]
                files_in_folder = os.listdir(folder_path)
                files_list = [
                    f"{folder_path}\\{found_file}"
                    for found_file in files_in_folder
                    if not os.path.isdir(f"{folder_path}\\{found_file}")
                ]
        else:
            log_and_print_error(
                "Invalid selection",
                "Please report this on github. Selection_Error",
            )
            sleep(5)
            return []
    if not files_list:
        log_and_print_error(
            "No file selected",
            "Please report this on github. Selection_Error",
        )
        sleep(5)
        return []
    return files_list

def select_sites(available: list) -> List[str]:
    questions = [
        inquirer.Checkbox(
            "selections",
            message=f"{colored('What sites do you want to upload too?', 'green')} "
            f"{colored(f'{len(available)} available', 'yellow')}",
            choices=available,
        ),
    ]
    answers = inquirer.prompt(questions)
    print("")
    return answers.get("selections", [])

def load_preset(config: dict, available: list) -> Tuple[list, str]:
    auto_load_preset = config.get("presetSystem", {}).get(
        "autoLoadPreset", False
    )
    preset_name = config.get("presetSystem", {}).get("presetName", "")
    if auto_load_preset and not os.path.exists(f"presets/{preset_name}"):
        print(
            colored(
                f"Error: Preset {preset_name} does not exist. "
                "Continuing without preset!",
                "red",
            )
        )
        print("")
        return available, ""
    if auto_load_preset and not DEBUG:
        auto_load_data = Preset_Manager.loader(available, preset_name)
        return auto_load_data[0], auto_load_data[1]
    return available, ""

def process_upload(
    file: str,
    site: str,
    config: dict,
    proxy_list: list,
    ua_list: list,
    link_format: str = "",
) -> None:
    bar_file_name = os.path.basename(file)
    api_key = (
        config.get("api_keys", {}).get(site)
        if sites_data_dict.get(site, {}).get("apiKey")
        else None
    )

    print(
        f"-> Uploading {colored(bar_file_name, 'light_blue')} to "
        f"{colored(site, 'yellow')}, please wait..."
    )

    uploader_classes = {
        "Pixeldrain": Pixeldrain,
        "Gofile": Gofile,
        "Oshi": Oshi,
        "FileBin": FileBin,
        "Delafil": Delafil,
        "Files.dp.ua": Files_dp_ua,
        "FilesFm": FilesFm,
        "Krakenfiles": Krakenfiles,
        "Transfer.sh": Transfer_sh,
        "TmpFiles": TmpFiles,
        "Mixdrop": Mixdrop,
        "1Fichier": OneFichier,
        "Fileio": Fileio,
        "EasyUpload": EasyUpload,
        "AnonTransfer": AnonTransfer,
        "1CloudFile": OneCloudFile,
        "Anonymfile": Anonymfile,
        "FileSi": FileSi,
        "FileUpload": FileUpload,
        "ClicknUpload": ClicknUpload,
        "BowFile": BowFile,
        "HexUpload": HexUpload,
        "UserCloud": UserCloud,
        "DooDrive": DooDrive,
        "uFile": uFile,
        "Download.gg": Download_gg,
        "Catbox": Catbox,
        "LitterBox": LitterBox,
        "Keep": Keep,
        "TempSend": TempSend,
        "UsersDrive": UsersDrive,
        "Rapidgator": Rapidgator,
        "WDHO": WDHO,
        "Filesadmin": Filesadmin,
        "Fastupload": Fastupload,
        "CyberFile": CyberFile,
        "Buzzheavier": Buzzheavier,
    }

    if site not in uploader_classes:
        print(f"{colored('Error:', 'red')} Site {site} not supported!")
        return

    try:
        output = uploader_classes[site].Uploader(
            file, proxy_list, ua_list, api_key
        )

        if not isinstance(output, dict):
            log_and_print_error(
                f"Invalid output type from {site}!",
                f"Expected a dictionary, got {type(output)}",
                output,
            )
            return

        status = output.get("status", "unknown_status")
        file_name = output.get("file_name", "unknown_file")
        file_url = output.get("file_url", "unknown_url")
        exception_str = output.get("exception", "no_exception")
        size_limit = output.get("size_limit", "unknown_size")
        extra = output.get("extra", "no_extra_info")

        if status == "ok":
            print(
                f"{ok} {colored(file_name, 'light_blue')} "
                f"{colored('successfully uploaded to', 'green')} "
                f"{colored(site, 'yellow')}"
                f"{colored('! URL:', 'green')} "
                f"{colored(file_url, 'light_blue')}"
            )
            with open("file_links.txt", "a") as file_links:
                file_links.writelines(
                    f"{datetime.now()} | {site} | {file_name} - "
                    f"{file_url}\n"
                )
            if link_format and not DEBUG:
                with open(
                    "file_links_formatted.txt", "a"
                ) as formatted_links_file:
                    formatted_links_file.writelines(
                        f"{link_format.format(status=status, file_name=file_name, file_url=file_url, site_name=site, date_and_time=datetime.now())}\n"
                    )
        elif status == "error":
            if site in ["Transfer_sh", "Keep"]:
                print(
                    f"{error} {colored(site, 'yellow')} fucked up "
                    "again while uploading the file "
                    f"{colored(file_name, 'light_blue')}. Don't "
                    "Report this! Its a known issue they need to fix."
                )
            else:
                log_and_print_error(
                    f"An error occurred while uploading the file "
                    f"{file_name} to {site}!",
                    exception_str,
                    extra,
                )
        elif status == "size_error":
            log_and_print_error(
                f"File size of {file_name} to big for {site}! "
                f"Compress it to fit the max size of "
                f"{size_limit}",
                exception_str,
                extra,
            )
        else:
            log_and_print_error(
                f"An unknown error occured while uploading the "
                f"file {file_name} to {site}!",
                exception_str,
                extra,
            )
    except Exception as e:
        log_and_print_error(
            f"An unexpected error occurred during upload to {site}",
            str(e),
        )

def upload_files(
    files_list: list,
    sites: list,
    config: dict,
    proxy_list: list,
    ua_list: list,
    link_format: str,
) -> None:
    with alive_bar(
        len(files_list),
        calibrate=1,
        dual_line=True,
        title="Uploading",
        enrich_print=False,
        stats=False,
        receipt=False,
        receipt_text=False,
    ) as list_bar:
        for file in files_list:
            for site in sites:
                process_upload(
                    file, site, config, proxy_list, ua_list, link_format
                )
            list_bar()

# ----------------------------------------------------------------------
# MAIN FUNCTION
# ----------------------------------------------------------------------

def main():
    try:
        set_window_title()
        config = load_configuration()
        check_for_updates(config)
        proxy_list, ua_list = fetch_resources(config)
        available_sites = check_availability(config, proxy_list, ua_list)
        setup_presets_directory()

        while True:
            available_sites, link_format = load_preset(
                config, available_sites
            )
            files_list = select_files()
            if not files_list:
                continue
            sites = select_sites(available_sites)
            if not sites:
                continue
            upload_files(
                files_list,
                sites,
                config,
                proxy_list,
                ua_list,
                link_format,
            )
            print("")
            print("")
    except KeyboardInterrupt:
        print("User Cancelled")
        sleep(3)
        exit(0)

if __name__ == "__main__":
    main()
