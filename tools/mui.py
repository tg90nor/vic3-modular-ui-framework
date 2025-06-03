#!/usr/bin/env python3
# mui_sync.py

import click
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

# --- Configuration ---
CONFIG_FILE_NAME = "mui_config.json" # For the framework itself
DEPENDENT_MOD_CONFIG_FILE_NAME = "mui_import_config.json" # For dependent mods

DEFAULT_CONFIG = { # For mui_config.json
  "victoria3": {
    "app_id": "529340",
    "game_path_override": None,
    "game_install_dir": None,
    "game_content_dir": None,
    "version": None
  },
  "framework": {
    "name": "vic3-modular-ui-framework",
    "base_game_files_dir": "vanilla_files", 
    "patches_dir": "patches",             
    "mod_source_dir": "gui", # Primary directory for the mod's UI files (e.g. <repo_root>/gui/)             
    "tracked_files": [                  # Paths relative to repo root (e.g. "gui/file.gui")
      "gui/information_panel_bar.gui",
      "gui/market_panel.gui",
      "gui/states_panel.gui"
    ],
    "framework_specific_files": [ # Files unique to your framework, also paths from repo root
        "gui/modular_ui_framework_types.gui"
    ]
  },
}

# --- Utility Functions ---

def load_config(config_file_name: str = CONFIG_FILE_NAME) -> dict:
    """Loads a specified JSON configuration file."""
    config_path = Path(config_file_name)
    if not config_path.exists():
        click.echo(f"Configuration file '{config_file_name}' not found.", err=True)
        if config_file_name == CONFIG_FILE_NAME:
             click.echo(f"Run 'mui.py init' to create one for the framework.")
        elif config_file_name == DEPENDENT_MOD_CONFIG_FILE_NAME:
            click.echo(f"Ensure this command is run from a dependent mod's root directory and '{DEPENDENT_MOD_CONFIG_FILE_NAME}' exists.")
        raise click.exceptions.Exit(1)
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        click.echo(f"Error: Could not parse '{config_file_name}'. Ensure it's valid JSON.", err=True)
        raise click.exceptions.Exit(1)
    except Exception as e:
        click.echo(f"Error loading config '{config_file_name}': {e}", err=True)
        raise click.exceptions.Exit(1)

def save_config(config_data: dict, config_file_name: str = CONFIG_FILE_NAME):
    """Saves configuration data to a specified JSON file."""
    config_path = Path(config_file_name)
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
    except Exception as e:
        click.echo(f"Error saving config to '{config_file_name}': {e}", err=True)
        raise click.exceptions.Exit(1)

def find_steam_root() -> Path | None:
    """
    Finds the Steam root directory based on the operating system.
    Returns: Path object to Steam root or None if not found.
    """
    system = platform.system()
    home = Path.home()
    steam_root = None

    if system == "Linux":
        possible_paths = [
            home / ".steam" / "steam",
            home / ".local" / "share" / "Steam"
        ]
        for p_path in possible_paths:
            if p_path.is_dir():
                steam_root = p_path
                break
    elif system == "Windows":
        program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
        program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        possible_paths = [
            program_files_x86 / "Steam",
            program_files / "Steam"
        ]
        try:
            import winreg
            key_path = r"Software\Valve\Steam"
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    steam_path_value, _ = winreg.QueryValueEx(key, "SteamPath")
                    if steam_path_value:
                        possible_paths.insert(0, Path(steam_path_value)) 
            except FileNotFoundError:
                pass 
        except ImportError:
            click.echo("Warning: 'winreg' module not found. Cannot check registry for Steam path on Windows.", err=True)

        for p_path in possible_paths:
            if p_path.is_dir() and (p_path / "steamapps").is_dir():
                steam_root = p_path
                break
    elif system == "Darwin": # macOS
        steam_root = home / "Library" / "Application Support" / "Steam"
        if not steam_root.is_dir():
            steam_root = None 
    
    if steam_root and not (steam_root / "steamapps" / "libraryfolders.vdf").exists():
        if not (steam_root / "libraryfolders.vdf").exists():
            pass # File might be in steam_root directly, handled by find_game_install_dir

    if not steam_root:
        click.echo("Error: Steam root directory not found.", err=True)
    return steam_root

def find_game_install_dir(app_id: str, steam_root_override: Path | None = None) -> Path | None:
    """
    Finds the game installation directory for the given app_id.
    Returns: Path to the game's base install directory (e.g., /path/to/Victoria3), not including 'game'.
    """
    steam_root = steam_root_override or find_steam_root()
    if not steam_root:
        return None

    library_folders_vdf = steam_root / "steamapps" / "libraryfolders.vdf"
    if not library_folders_vdf.exists():
        library_folders_vdf = steam_root / "libraryfolders.vdf" # Check alternative location
        if not library_folders_vdf.exists():
            click.echo(f"Error: libraryfolders.vdf not found at {steam_root / 'steamapps'} or {steam_root}", err=True)
            return None

    library_paths = []
    default_steamapps_parent = steam_root / "steamapps"
    if default_steamapps_parent.is_dir(): # The parent of steamapps is a library path
        library_paths.append(default_steamapps_parent.parent) 

    try:
        with open(library_folders_vdf, 'r', encoding='utf-8') as f:
            content = f.read()
        path_matches = re.findall(r'"path"\s*"([^"]+)"', content, re.IGNORECASE)
        for path_str in path_matches:
            lib_path = Path(path_str.replace("\\\\", "\\")) 
            if lib_path.is_dir():
                library_paths.append(lib_path)
    except Exception as e:
        click.echo(f"Error reading or parsing {library_folders_vdf}: {e}", err=True)

    game_install_path = None
    for lib_path_root in library_paths:
        manifest_file = lib_path_root / "steamapps" / f"appmanifest_{app_id}.acf"
        if manifest_file.is_file():
            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest_content = f.read()
                installdir_match = re.search(r'"installdir"\s*"([^"]+)"', manifest_content, re.IGNORECASE)
                if installdir_match:
                    game_subdir_name = installdir_match.group(1)
                    possible_path = lib_path_root / "steamapps" / "common" / game_subdir_name
                    if possible_path.is_dir():
                        game_install_path = possible_path
                        break 
            except Exception as e:
                click.echo(f"Error reading or parsing manifest {manifest_file}: {e}", err=True)
                continue 

    if not game_install_path:
        click.echo(f"Error: Game (App ID {app_id}) installation directory not found.", err=True)
    return game_install_path

def get_victoria3_version(game_install_dir: Path) -> str | None:
    """
    Gets the Victoria 3 version from caligula_branch.txt.
    game_install_dir: Path to the game's base installation directory (e.g. /path/to/Victoria3)
    """
    if not game_install_dir or not game_install_dir.is_dir():
        click.echo("Error: Invalid game installation directory provided for version check.", err=True)
        return None

    version_file = game_install_dir / "launcher" / "caligula_branch.txt" 
    if not version_file.is_file():
        version_file_alt = game_install_dir / "caligula_branch.txt"
        if version_file_alt.is_file():
            version_file = version_file_alt
        else:
            click.echo(f"Error: Version file '{version_file.name}' not found in '{version_file.parent}' or '{version_file_alt.parent}'.", err=True)
            return None
    
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            content = f.read()
        version_match = re.search(r'release/(\d+\.\d+(?:\.\d+)*)', content)
        if version_match:
            return version_match.group(1)
        else:
            click.echo(f"Error: Could not extract version from '{version_file}'. Content:\n{content[:200]}...", err=True)
            return None
    except Exception as e:
        click.echo(f"Error reading version file {version_file}: {e}", err=True)
        return None

def ensure_game_info(config: dict, check_version: bool = True) -> tuple[Path, str | None]:
    """
    Checks if game content directory and optionally version are in config.
    Raises click.exceptions.Exit(1) if not found or invalid.
    Returns: (game_content_dir_path, game_version_str | None)
    """
    game_content_dir_str = config["victoria3"].get("game_content_dir")
    game_version = config["victoria3"].get("version")

    if not game_content_dir_str:
        click.echo("Error: Game content directory not found in main mui_config.json. "
                   "Please run 'mui.py locate-game' in the framework directory first.", err=True)
        raise click.exceptions.Exit(1)
    
    game_content_dir = Path(game_content_dir_str)
    if not game_content_dir.is_dir(): 
        click.echo(f"Error: Configured game content directory '{game_content_dir}' from main mui_config.json does not exist or is not a directory. "
                   "Please re-run 'mui.py locate-game' in the framework directory.", err=True)
        raise click.exceptions.Exit(1)
    
    if check_version and not game_version:
        click.echo("Error: Game version not found in main mui_config.json. "
                   "Please run 'mui.py locate-game' in the framework directory first.", err=True)
        raise click.exceptions.Exit(1)
        
    return game_content_dir, game_version

def check_git_availability():
    """Checks if git is available on the system path."""
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True, text=True, encoding='utf-8')
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        click.echo("Error: `git` command not found or not executable. Please ensure Git is installed and in your PATH.", err=True)
        return False

# --- CLI Commands ---

@click.group()
def cli():
    """
    Modular UI Synchronizer (mui.py) for Victoria 3.
    Helps manage UI framework files, patches, and distribution to dependent mods.
    This tool should typically be run from the root of the vic3-modular-ui-framework repository,
    EXCEPT for the 'distribute' command, which is run from a dependent mod's directory.
    """
    pass

@cli.command()
def init():
    """Initializes mui.py in the current directory (framework's root).
    Creates mui_config.json and necessary directories.
    """
    config_path = Path(CONFIG_FILE_NAME)
    if config_path.exists():
        if not click.confirm(f"'{CONFIG_FILE_NAME}' already exists. Overwrite with defaults? (This will reset your config)"):
            click.echo("Initialization aborted.")
            return
    
    try:
        current_default_config = json.loads(json.dumps(DEFAULT_CONFIG))
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(current_default_config, f, indent=2)
        click.echo(f"Created default configuration file: '{CONFIG_FILE_NAME}'")

        for d_path_str in [current_default_config["framework"]["base_game_files_dir"],
                           current_default_config["framework"]["patches_dir"],
                           current_default_config["framework"]["mod_source_dir"]]: 
            d_path = Path(d_path_str)
            d_path.mkdir(parents=True, exist_ok=True)
            click.echo(f"Ensured directory exists: '{d_path}'")
        
        for tf_str in current_default_config["framework"]["tracked_files"] + \
                      current_default_config["framework"]["framework_specific_files"]:
            target_file_path = Path(tf_str) 
            target_file_path.parent.mkdir(parents=True, exist_ok=True)


        click.echo("Initialization complete. Please review and customize mui_config.json.")
        click.echo("Ensure 'tracked_files' in mui_config.json are paths relative to the repository root (e.g., 'gui/your_file.gui').")
        click.echo("Next, try 'mui.py locate-game' to find your Victoria 3 installation.")

    except Exception as e:
        click.echo(f"Error during initialization: {e}", err=True)
        raise click.exceptions.Exit(1)


@cli.command(name="locate-game")
@click.option('--steam-path', help="Manually specify Steam root path.", type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--game-path-override', help="Manually specify Victoria 3 installation path (e.g., /path/to/Victoria3).", type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True))
def locate_game_command(steam_path, game_path_override):
    """
    Locates the Victoria 3 game installation and version.
    Updates mui_config.json (in framework root) with the found paths and version.
    """
    config = load_config(CONFIG_FILE_NAME) 
    app_id = config["victoria3"].get("app_id", DEFAULT_CONFIG["victoria3"]["app_id"])

    if game_path_override:
        vic3_install_dir = Path(game_path_override)
        click.echo(f"Using provided game installation path: {vic3_install_dir}")
    elif config["victoria3"].get("game_path_override"):
        vic3_install_dir = Path(config["victoria3"]["game_path_override"])
        click.echo(f"Using game installation path from config: {vic3_install_dir}")
    else:
        click.echo("Attempting to auto-detect Victoria 3 installation...")
        steam_root_path_obj = Path(steam_path) if steam_path else None
        vic3_install_dir = find_game_install_dir(app_id, steam_root_override=steam_root_path_obj)

    if vic3_install_dir and vic3_install_dir.is_dir():
        click.echo(f"Victoria 3 installation found: {vic3_install_dir}")
        config["victoria3"]["game_install_dir"] = str(vic3_install_dir.resolve())
        
        game_content_dir = vic3_install_dir / "game"
        if game_content_dir.is_dir():
            config["victoria3"]["game_content_dir"] = str(game_content_dir.resolve())
            click.echo(f"Victoria 3 game content directory set to: {game_content_dir.resolve()}")
        else:
            click.echo(f"Warning: 'game' subdirectory not found in {vic3_install_dir}. "
                       f"Game content path might be incorrect.", err=True)
            config["victoria3"]["game_content_dir"] = str(vic3_install_dir.resolve()) 

        version = get_victoria3_version(vic3_install_dir)
        if version:
            click.echo(f"Victoria 3 version detected: {version}")
            config["victoria3"]["version"] = version
        else:
            click.echo("Could not detect Victoria 3 version automatically.", err=True)
            config["victoria3"]["version"] = None 
    else:
        click.echo("Failed to locate Victoria 3 installation directory.", err=True)
        config["victoria3"]["game_install_dir"] = None
        config["victoria3"]["game_content_dir"] = None
        config["victoria3"]["version"] = None

    save_config(config, CONFIG_FILE_NAME)
    if not vic3_install_dir: 
        raise click.exceptions.Exit(1)

@cli.command(name="fetch-vanilla")
@click.option('--force', is_flag=True, help="Force overwrite if vanilla files for this version already exist.")
def fetch_vanilla_command(force):
    """
    Fetches tracked GUI files from the game directory into the
    versioned 'vanilla_files' directory (within the framework).
    """
    config = load_config(CONFIG_FILE_NAME) 
    
    try:
        game_content_dir, game_version = ensure_game_info(config)
    except click.exceptions.Exit:
        return 

    base_vanilla_dir = Path(config["framework"]["base_game_files_dir"])
    versioned_vanilla_dir = base_vanilla_dir / game_version
    tracked_files_rel_paths = config["framework"].get("tracked_files", [])


    if not tracked_files_rel_paths:
        click.echo("No files are currently tracked in the configuration ('framework.tracked_files'). Nothing to fetch.")
        return

    if versioned_vanilla_dir.exists() and any(versioned_vanilla_dir.iterdir()) and not force:
        if not click.confirm(
            f"Vanilla files for version '{game_version}' already exist at '{versioned_vanilla_dir}'.\n"
            f"Do you want to overwrite them? (Use --force to skip this prompt)"
        ):
            click.echo("Fetch operation aborted by user.")
            return
        click.echo(f"Overwriting existing vanilla files for version '{game_version}' as confirmed by user.")
    elif versioned_vanilla_dir.exists() and any(versioned_vanilla_dir.iterdir()) and force:
        click.echo(f"Overwriting existing vanilla files for version '{game_version}' due to --force.")
    
    versioned_vanilla_dir.mkdir(parents=True, exist_ok=True)
    click.echo(f"Fetching vanilla files for version '{game_version}' into '{versioned_vanilla_dir}'...")

    success_count = 0
    fail_count = 0

    for rel_file_path_str in tracked_files_rel_paths: 
        source_file = game_content_dir / rel_file_path_str 
        dest_file = versioned_vanilla_dir / rel_file_path_str
        
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        if source_file.is_file():
            try:
                shutil.copy2(source_file, dest_file) 
                click.echo(f"  Copied: '{rel_file_path_str}' to '{dest_file}'")
                success_count += 1
            except Exception as e:
                click.echo(f"  Error copying '{rel_file_path_str}': {e}", err=True)
                fail_count += 1
        else:
            click.echo(f"  Source file not found: '{source_file}' (skipped)", err=True)
            fail_count += 1
            
    click.echo("-" * 20) 
    if success_count > 0:
        click.echo(f"Successfully fetched {success_count} file(s).")
    if fail_count > 0:
        click.echo(f"Failed to fetch {fail_count} file(s). Please check errors above.", err=True)
    
    if fail_count > 0:
        raise click.exceptions.Exit(1)

@cli.command(name="create-patch")
@click.argument('files', nargs=-1, type=click.Path()) 
def create_patch_command(files):
    """
    Creates patch files by comparing framework's source files (e.g. gui/file.gui)
    against fetched vanilla files for the current version.
    Run from the framework's root directory.
    """
    config = load_config(CONFIG_FILE_NAME) 
    try:
        _, game_version = ensure_game_info(config) 
    except click.exceptions.Exit:
        return

    vanilla_base_dir = Path(config["framework"]["base_game_files_dir"])
    vanilla_version_dir = vanilla_base_dir / game_version
    patches_base_dir = Path(config["framework"]["patches_dir"])
    patches_version_dir = patches_base_dir / game_version

    config_tracked_files = config["framework"].get("tracked_files", [])
    if files: 
        files_to_process_str = [Path(f).as_posix() for f in files]
    else:
        files_to_process_str = config_tracked_files 

    if not files_to_process_str:
        click.echo("No files specified or configured for patching.")
        return

    patches_version_dir.mkdir(parents=True, exist_ok=True)
    click.echo(f"Creating patches for version '{game_version}' into '{patches_version_dir}'...")

    success_count = 0
    no_diff_count = 0
    fail_count = 0

    for rel_path_str in files_to_process_str: 
        original_file_abs_path = (vanilla_version_dir / rel_path_str).resolve()
        modified_file_abs_path = Path(rel_path_str).resolve() 
        
        patch_output_file = patches_version_dir / (rel_path_str + ".patch")

        if not original_file_abs_path.is_file():
            click.echo(f"  Vanilla file not found: '{original_file_abs_path}'. Skipping patch for '{rel_path_str}'.", err=True)
            fail_count += 1
            continue
        if not modified_file_abs_path.is_file():
            click.echo(f"  Modded file not found: '{modified_file_abs_path}'. Skipping patch for '{rel_path_str}'.", err=True)
            fail_count += 1
            continue

        patch_output_file.parent.mkdir(parents=True, exist_ok=True)
        
        label_a = f"a/{vanilla_base_dir.name}/{game_version}/{rel_path_str}" 
        label_b = f"b/{rel_path_str}" 

        click.echo(f"  Diffing: '{original_file_abs_path.relative_to(Path.cwd())}' vs '{modified_file_abs_path.relative_to(Path.cwd())}'")
        try:
            process = subprocess.run(
                ['diff', '-u', 
                 '--label', label_a, str(original_file_abs_path), 
                 '--label', label_b, str(modified_file_abs_path)],
                capture_output=True, text=True, encoding='utf-8', check=False 
            )

            if process.returncode == 0:
                click.echo(f"  No differences found for '{rel_path_str}'. Patch not created.")
                if patch_output_file.exists():
                    patch_output_file.unlink()
                no_diff_count +=1
            elif process.returncode == 1: 
                with open(patch_output_file, 'w', encoding='utf-8', newline='\n') as f_patch: 
                    f_patch.write(process.stdout)
                click.echo(f"  Patch created: '{patch_output_file}'")
                success_count += 1
            else: 
                click.echo(f"  Error creating patch for '{rel_path_str}'. `diff` exit code: {process.returncode}", err=True)
                if process.stderr:
                    click.echo(f"  `diff` stderr:\n{process.stderr}", err=True)
                fail_count += 1
        except FileNotFoundError:
            click.echo("Error: `diff` command not found. Please ensure it's installed and in your PATH.", err=True)
            raise click.exceptions.Exit(10) 
        except Exception as e:
            click.echo(f"  An unexpected error occurred while creating patch for '{rel_path_str}': {e}", err=True)
            fail_count += 1

    click.echo("-" * 20)
    if success_count > 0:
        click.echo(f"Successfully created {success_count} patch(es).")
    if no_diff_count > 0:
        click.echo(f"{no_diff_count} file(s) had no differences.")
    if fail_count > 0:
        click.echo(f"Failed to process {fail_count} file(s) for patching.", err=True)
    
    if fail_count > 0:
        raise click.exceptions.Exit(1)

@cli.command(name="apply-patch")
@click.option('--source-patch-version', help="Specify game version of patches to apply (defaults to current game version).")
@click.argument('files', nargs=-1, type=click.Path())
def apply_patch_command(source_patch_version, files):
    """
    Applies patches to framework's source files using `git apply`.
    Run from the framework's root directory.
    """
    if not check_git_availability():
        raise click.exceptions.Exit(10) 

    config = load_config(CONFIG_FILE_NAME) 
    try:
        _, current_game_version = ensure_game_info(config) 
    except click.exceptions.Exit:
        return

    if not source_patch_version:
        source_patch_version = current_game_version 
        click.echo(f"No --source-patch-version specified, using current game version for patches: {source_patch_version}")
    else:
        click.echo(f"Attempting to apply patches from version: {source_patch_version}")

    vanilla_base_dir = Path(config["framework"]["base_game_files_dir"])
    current_vanilla_version_dir = vanilla_base_dir / current_game_version
    
    patches_base_dir = Path(config["framework"]["patches_dir"])
    source_patches_version_dir = patches_base_dir / source_patch_version

    config_tracked_files = config["framework"].get("tracked_files", [])
    if files: 
        files_to_process_str = [Path(f).as_posix() for f in files]
    else:
        files_to_process_str = config_tracked_files

    if not files_to_process_str:
        click.echo("No files specified or configured for applying patches.")
        return

    click.echo(f"Applying patches from '{source_patches_version_dir}' to files based on vanilla version '{current_game_version}'...")

    success_count = 0
    conflict_count = 0
    fail_count = 0
    missing_patch_count = 0
    missing_vanilla_count = 0

    for rel_path_str in files_to_process_str: 
        target_mod_file = Path(rel_path_str) 
        vanilla_source_file = current_vanilla_version_dir / rel_path_str
        patch_file_to_apply = source_patches_version_dir / (rel_path_str + ".patch")

        click.echo(f"Processing '{target_mod_file}':")

        if not vanilla_source_file.is_file():
            click.echo(f"  ERROR: Current vanilla file '{vanilla_source_file}' not found. Cannot apply patch. "
                       f"Run 'fetch-vanilla' for version {current_game_version}.", err=True)
            missing_vanilla_count +=1
            fail_count +=1
            continue
        
        if not patch_file_to_apply.is_file():
            click.echo(f"  INFO: Patch file '{patch_file_to_apply}' not found. "
                       f"'{target_mod_file}' will be a copy of the current vanilla file.") 
            missing_patch_count +=1
            try:
                target_mod_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(vanilla_source_file, target_mod_file)
                click.echo(f"  Copied vanilla '{vanilla_source_file.name}' to '{target_mod_file}'.")
            except Exception as e:
                click.echo(f"  Error copying vanilla file '{vanilla_source_file.name}' to '{target_mod_file}': {e}", err=True)
                fail_count +=1
            continue 

        try:
            target_mod_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(vanilla_source_file, target_mod_file)
            click.echo(f"  Prepared '{target_mod_file}' with content from vanilla version '{current_game_version}'.")
        except Exception as e:
            click.echo(f"  Error preparing target file '{target_mod_file}': {e}", err=True)
            fail_count += 1
            continue
            
        try:
            # Run git apply from the repository root (current working directory)
            # The paths in the patch (e.g., +++ b/gui/file.gui) are expected to be relative to this root.
            check_process = subprocess.run(
                ['git', 'apply', '--check', str(patch_file_to_apply.resolve())], # Use resolved path for patch file
                capture_output=True, text=True, encoding='utf-8', check=False, cwd=Path.cwd()
            )
            
            if check_process.returncode != 0:
                 click.echo(f"  WARNING: Patch '{patch_file_to_apply.name}' may not apply cleanly. `git apply --check` failed.")
                 if check_process.stderr:
                    click.echo(f"  `git apply --check` stderr:\n{check_process.stderr.strip()}", err=True)

            apply_process = subprocess.run(
                ['git', 'apply', '--verbose', '--reject', '--whitespace=fix', str(patch_file_to_apply.resolve())],
                capture_output=True, text=True, encoding='utf-8', check=False, cwd=Path.cwd()
            )

            applied_cleanly = apply_process.returncode == 0
            # .rej files are created relative to the target file's location
            rej_file_exists = (target_mod_file.parent / (target_mod_file.name + ".rej")).exists()


            if applied_cleanly and not rej_file_exists:
                click.echo(f"  Successfully applied patch '{patch_file_to_apply.name}' to '{target_mod_file}'.")
                success_count += 1
            elif applied_cleanly and rej_file_exists: # Applied with rejections
                click.echo(f"  CONFLICTS: Patch for '{target_mod_file.name}' applied but resulted in conflicts. Check '{target_mod_file.name}.rej'.", err=True)
                conflict_count +=1
            else: # apply_process.returncode != 0 (failed to apply)
                click.echo(f"  ERROR: Failed to apply patch '{patch_file_to_apply.name}' to '{target_mod_file}'. `git apply` exit code: {apply_process.returncode}", err=True)
                if apply_process.stdout: click.echo(f"  `git apply` stdout:\n{apply_process.stdout.strip()}", err=True)
                if apply_process.stderr: click.echo(f"  `git apply` stderr:\n{apply_process.stderr.strip()}", err=True)
                fail_count += 1
                if rej_file_exists: # If it failed but still created .rej
                     click.echo(f"  CONFLICTS: Check '{target_mod_file.name}.rej' for unapplied changes.", err=True)


        except FileNotFoundError: 
            click.echo("Error: `git` command not found. This should have been caught earlier.", err=True)
            raise click.exceptions.Exit(10)
        except Exception as e:
            click.echo(f"  An unexpected error occurred while applying patch for '{rel_path_str}': {e}", err=True)
            fail_count += 1

    click.echo("-" * 20)
    if success_count > 0:
        click.echo(f"Successfully applied patches for {success_count} file(s).")
    if conflict_count > 0:
        click.echo(f"{conflict_count} file(s) had conflicts during patching (see .rej files).", err=True)
    if missing_patch_count > 0:
        click.echo(f"{missing_patch_count} file(s) had no corresponding patch file and were set to vanilla content.")
    if missing_vanilla_count > 0:
        click.echo(f"{missing_vanilla_count} file(s) were skipped due to missing current vanilla files.", err=True)
    
    # Consolidate failure reporting
    total_problematic_files = fail_count + conflict_count + missing_vanilla_count
    if total_problematic_files > 0 and success_count < len(files_to_process_str): # If not all files were successful
        # The individual error messages above are more specific.
        # This general message indicates that the operation wasn't fully successful.
        pass # Detailed messages already printed

    if fail_count > 0 or conflict_count > 0 or missing_vanilla_count > 0:
        raise click.exceptions.Exit(1)

@cli.command()
def distribute():
    """
    Distributes specified files from the Modular UI Framework
    to the current dependent mod.
    This command MUST be run from the root directory of the dependent mod.
    It requires a 'mui_import_config.json' file in that directory.
    """

    try:
        # Load the dependent mod's import configuration
        dep_config = load_config(DEPENDENT_MOD_CONFIG_FILE_NAME)
    except click.exceptions.Exit:
        return

    framework_path_str = dep_config.get("modular_ui_framework_path")
    files_to_copy_list = dep_config.get("files_to_copy", [])

    if not framework_path_str:
        click.echo(f"Error: 'modular_ui_framework_path' not defined in '{DEPENDENT_MOD_CONFIG_FILE_NAME}'.", err=True)
        raise click.exceptions.Exit(1)
    
    if not files_to_copy_list:
        click.echo(f"Warning: 'files_to_copy' is empty or not defined in '{DEPENDENT_MOD_CONFIG_FILE_NAME}'. Nothing to distribute.")
        return

    framework_dir = Path(framework_path_str).resolve()

    if not framework_dir.is_dir():
        click.echo(f"Error: Modular UI Framework directory not found at resolved path: '{framework_dir}'. "
                   f"Check 'modular_ui_framework_path' in '{DEPENDENT_MOD_CONFIG_FILE_NAME}'.", err=True)
        raise click.exceptions.Exit(1)

    framework_main_config_path = framework_dir / CONFIG_FILE_NAME
    if not framework_main_config_path.is_file():
        click.echo(f"Warning: The main '{CONFIG_FILE_NAME}' not found in the specified framework directory '{framework_dir}'. "
                   f"The path might be incorrect or the framework is not initialized.", err=True)

    success_count = 0
    fail_count = 0

    for item in files_to_copy_list:
        source_rel_path_str = item.get("source_from_framework")
        target_rel_path_str = item.get("target_in_this_mod")

        if not source_rel_path_str or not target_rel_path_str:
            click.echo("  Error: Invalid item in 'files_to_copy' (missing source or target). Skipping.", err=True)
            fail_count += 1
            continue

        source_rel_path = Path(framework_path_str) / source_rel_path_str
        source_abs_path = framework_dir / source_rel_path_str
        target_abs_path = Path.cwd() / target_rel_path_str

        if not source_abs_path.is_file():
            click.echo(f"    ERROR: Source file not found in framework: '{source_abs_path}'. Skipping.", err=True)
            fail_count += 1
            continue
        
        try:
            target_abs_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_abs_path, target_abs_path) 
            click.echo(f"    Copied '{source_rel_path}' -> '{target_rel_path_str}'.")
            success_count += 1
        except Exception as e:
            click.echo(f"    ERROR copying '{source_rel_path_str}': {e}", err=True)
            fail_count += 1

    click.echo("-" * 20)
    if success_count > 0:
        click.echo(f"Successfully distributed {success_count} file(s).")
    if fail_count > 0:
        click.echo(f"Failed to distribute {fail_count} file(s). Please check errors above.", err=True)

    if fail_count > 0:
        raise click.exceptions.Exit(1)


if __name__ == '__main__':
    cli()

