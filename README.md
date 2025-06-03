# Modular UI Framework & Sync Tool

This project consists of two main components for Victoria 3 modding: the **Modular UI Framework** itself, which provides extension hooks for other mods to add UI elements, and the **Modular UI Sync Tool (`mui`)**, a command-line utility for managing the framework's files and patches.

## 1. Modular UI Framework

The Modular UI Framework is designed to be as modular as possible, allowing for easy integration with other mods. It provides extension hooks that other mods can define as types in their GUI files, and these elements will then be displayed in the game.

### Extension hooks list

#### Sidebar

`gui/information_panel_bar.gui`

The sidebar is not dynamic, so any new button needs to be added to this mod.

| Hook Name | Suggested Type | Description |
| --- | --- | --- |
| more_spreadsheets_sidebar_button | widget | More Spreadsheets mod sidebar button |
| cheat_menu_sidebar_button | widget | Cheat Menu mod sidebar button |
| victoria_universalis_iv_sidebar_button | widget | Victoria Universalis IV mod sidebar button. |

#### Market Panel

`gui/market_panel.gui`

| Hook Name | Suggested Type | Description |
| --- | --- | --- |
| market_panel_header_top_left_button | widget | 30x30 button in the top left of the header, next to the Back button. |
| market_panel_header_bottom_left_button | widget | 30x30 button in the bottom left of the header, next to the Back button. |
| market_panel_details_content_override | container | Replaces the default Goods tab main content. |
| market_panel_trade_routes_content_override | container | Replaces the default Trade Routes tab main content. |
| market_panel_trade_routes_trade_suggestions_override | container | Replaces the default Highlights tab main content. |
| market_panel_states_content_override | container | Replaces the default Members tab main content. |

#### States Panel

`gui/states_panel.gui`

| Hook Name | Suggested Type | Description |
| --- | --- | --- |
| states_panel_header_top_left_button | widget | 30x30 button in the top left of the header, next to the Back button. |
| states_panel_header_bottom_left_button | widget | 30x30 button in the bottom left of the header, next to the Back button. |
| state_panel_overview_content_override | flowcontainer | Replaces the default Overview tab main content. |
| state_panel_condensed_override | flowcontainer | Replaces the condensed version of the Overview tab, which is not normally accessible. |
| state_panel_buildings_content_override | flowcontainer | Replaces the default Buildings tab main content. |
| state_panel_population_content_override | flowcontainer | Replaces the default Population tab main content. |
| state_panel_local_goods_content_override | flowcontainer | Replaces the default Local Prices tab main content. |
| state_panel_modifiers_content_override | flowcontainer | Replaces the default Information tab main content. |

### How to use (Framework)

To use these extension hooks, simply define one of the hooks as a `type` in your mod's GUI files.

**Example:** Adding a button to the top left of the Market Panel header.

Create a file like `gui/my_mod.gui` in your mod with the following content:

```
types my_mod {
  type market_panel_header_top_left_button = widget {
    # inactive variant
    button_icon_round = {
      size = { 100% 100% }
      tooltip = "MY_MOD_BUTTON_TOOLTIP"
      using = confirm_button_sound
      visible = "[Not(GetPlayer.MakeScope.Var('toggle_my_mod_function').IsSet)]"
      onclick = "[GetScriptedGui('toggle_my_mod_function').Execute( GuiScope.SetRoot( GetPlayer.MakeScope ).End )]"
      blockoverride "icon" {
        texture = "gfx/interface/buttons/button_icons/list.dds"
      }
    }
    # active variant
    button_icon_round_action = {
      size = { 100% 100%}
      tooltip = "MY_MOD_BUTTON_TOOLTIP"
      using = confirm_button_sound
      visible = "[GetPlayer.MakeScope.Var('toggle_my_mod_function').IsSet]"
      onclick = "[GetScriptedGui('toggle_my_mod_function').Execute( GuiScope.SetRoot( GetPlayer.MakeScope ).End )]"
      blockoverride "icon" {
        texture = "gfx/interface/buttons/button_icons/list.dds"
      }
      using = selected_sidepanel_animation_small_no_arrow
    }
  }
}

```

## 2. Modular UI Sync Tool (mui)

The Modular UI Sync Tool (`mui`) is a command-line utility designed to help manage the `vic3-modular-ui-framework` for Victoria 3. It assists with:

-   Fetching vanilla (base game) UI files.

-   Creating and applying patches for your framework's modifications.

-   Distributing the framework's files to dependent mods.


This tool is primarily intended for the maintainer of the `vic3-modular-ui-framework` but also provides a command for developers of mods that depend on the framework.

### Prerequisites (for `mui` tool)

Before using `mui`, ensure you have the following installed:

1.  **Python 3:** (e.g., Python 3.10 or newer).

2.  **pip:** Python's package installer (usually comes with Python).

3.  **Git:** For applying patches (`apply-patch` command). Must be in your system's PATH.

4.  **Diffutils:** Provides the `diff` command (for `create-patch` command).

    -   **Linux:** Usually pre-installed. If not, install via your package manager (e.g., `sudo apt install diffutils`).

    -   **macOS:** Comes with Xcode Command Line Tools.

    -   **Windows:** Git for Windows includes `diff`. Ensure its `usr/bin` directory (e.g., `C:\Program Files\Git\usr\bin`) is in your system's PATH.

5.  **Direnv (Recommended):** For easier environment management and PATH setup. See [direnv.net](https://direnv.net/ "null").


### Setup (`mui` tool)

The `mui` tool itself (`mui.py`) is located in the `tools/` directory of the `vic3-modular-ui-framework` repository. A wrapper script `tools/mui` and a `Pipfile` are provided for convenience.

#### For the Framework Maintainer (`vic3-modular-ui-framework`)

1.  **Clone the Framework Repository:**

    ```
    git clone <your-framework-repo-url> vic3-modular-ui-framework
    cd vic3-modular-ui-framework

    ```

2.  **Set up Direnv (Recommended):**

    -   Make sure you have `direnv` and `pipenv` installed.
    -   Allow direnv `.envrc` in repo and `tools` directories:

        ```bash
        # in vic3-modular-ui-framework directory
        direnv allow .
        cd tools
        direnv allow .
        cd ..
        ```

    -   This setup ensures that the `mui` command is available when you are in the framework's root directory and that `click` is installed in the environment `direnv` activates for the `tools` directory.

3.  Initialize the Tool:

    Run this from the root of the vic3-modular-ui-framework repository:

    ```
    mui init
    ```

    This creates:

    -   `mui_config.json`: Configuration file for the framework.

    -   `vanilla_files/`: Directory to store fetched base game UI files.

    -   `patches/`: Directory to store generated patch files.

    -   `gui/`: The primary working directory for your framework's modified UI files.

4.  Locate Game Installation:

    Run this from the root of the vic3-modular-ui-framework repository:

    ```
    mui locate-game
    ```

    This attempts to find your Victoria 3 installation and version, updating `mui_config.json`. If it fails, you can manually specify paths in `mui_config.json` or use options with the command.


#### For Dependent Mod Developers

1.  **Ensure Framework is Available:** Make sure you have a local copy of the `vic3-modular-ui-framework` repository.

2.  **Set up Direnv in Your Mod (Recommended):**

    -   In the **root directory of your dependent mod**, create/update your `.envrc` file:

        ```bash
        # In <your_mod_root>/.envrc
        # Adjust the path to your local clone of the framework
        export MODULAR_UI_PATH="../vic3-modular-ui-framework"
        PATH_add "$MODULAR_UI_PATH/tools"
        ```

    -   Allow `direnv`:

        ```bash
        cd /path/to/your-dependent-mod
        direnv allow .
        ```


    This makes the `mui` command available when you are in your mod's directory.

3.  Create Import Configuration:

    In the root directory of your dependent mod, create a file named mui_import_config.json:

    ```json
    {
      "modular_ui_framework_path": "../vic3-modular-ui-framework", // Relative path to the framework repo
      "files_to_copy": [
        {
          "source_from_framework": "gui/information_panel_bar.gui", // Path within the framework
          "target_in_this_mod": "gui/information_panel_bar.gui"    // Path within your mod
        },
        {
          "source_from_framework": "gui/modular_ui_framework_types.gui",
          "target_in_this_mod": "gui/modular_ui_framework_types.gui"
        }
        // Add more files as needed
      ]
    }

    ```

    -   `modular_ui_framework_path`: The relative path from your dependent mod's root to the `vic3-modular-ui-framework` root.

    -   `files_to_copy`: A list of files to copy from the framework to your mod.

        -   `source_from_framework`: The path of the file within the framework's structure (e.g., `gui/file.gui` refers to `<framework_root>/gui/file.gui`).

        -   `target_in_this_mod`: The desired path for the file within your dependent mod.


### Configuration Files (`mui` tool)

#### `mui_config.json` (Framework Root)

This file configures the behavior of `mui` for the `vic3-modular-ui-framework` itself.

```json
{
  "victoria3": {
    "app_id": "529340",
    "game_path_override": null, // Manually set game install dir if auto-detection fails
    "game_install_dir": null,   // Auto-detected game install directory
    "game_content_dir": null,   // Auto-detected game content directory (e.g., .../Victoria3/game)
    "version": null             // Auto-detected game version
  },
  "framework": {
    "name": "vic3-modular-ui-framework",
    "base_game_files_dir": "vanilla_files", // Stores fetched vanilla files
    "patches_dir": "patches",             // Stores generated .patch files
    "mod_source_dir": "gui",              // Root for your framework's moddable files (e.g. <repo_root>/gui/)
    "tracked_files": [                  // Files to patch, paths relative to repo root
      "gui/information_panel_bar.gui",
      "gui/market_panel.gui"
    ],
    "framework_specific_files": [       // Framework-only files, paths relative to repo root
        "gui/modular_ui_framework_types.gui"
    ]
  }
}

```

-   **`tracked_files`**: A list of game files (paths relative to the repository root, e.g., `gui/file.gui`) that your framework modifies. These are the files for which patches will be created and applied.

-   **`framework_specific_files`**: Files that are unique to your framework (not patched from vanilla game files) but might be distributed to dependent mods. Paths are relative to the repository root.

-   **`mod_source_dir`**: The primary directory within your framework repository where your modified (target) versions of `tracked_files` and `framework_specific_files` are located (e.g., `gui` means files like `gui/information_panel_bar.gui` are directly at `<framework_root>/gui/information_panel_bar.gui`).


#### `mui_import_config.json` (Dependent Mod Root)

As described in the "For Dependent Mod Developers" setup section, this file tells `mui distribute` where to find the framework and which files to copy.

### Workflow & Commands (`mui` tool)

#### For Framework Maintainers (run from framework root)

1.  **`mui init`**

    -   Initializes the directory structure and `mui_config.json`. Run once.

2.  **`mui locate-game`**

    -   Detects Victoria 3 installation path and version, saving them to `mui_config.json`. Run after `init` and if your game path changes.

3.  **`mui fetch-vanilla`**

    -   Copies the `tracked_files` from the detected game installation into `vanilla_files/<current_game_version>/`.

    -   Run this after each game update to get the latest base files.

    -   Use `--force` to overwrite existing fetched files for the current version without prompting.

4.  **Edit Framework Files**

    -   Make your modifications to the UI files directly within the framework's source directory (e.g., in `<framework_root>/gui/information_panel_bar.gui` if `mod_source_dir` is `gui` and `tracked_files` contains `gui/information_panel_bar.gui`).

5.  **`mui create-patch [file1 file2 ...]`**

    -   Compares your modified files (e.g., in `<framework_root>/gui/`) against the corresponding vanilla files in `vanilla_files/<current_game_version>/`.

    -   Generates `.patch` files and saves them to `patches/<current_game_version>/`.

    -   If no specific files are listed, it processes all `tracked_files`.

    -   Example: `mui create-patch gui/market_panel.gui`

6.  **`mui apply-patch [--source-patch-version <version>] [file1 file2 ...]`**

    -   Applies patches to your framework's working files. This is crucial for updating your framework after a game update.

    -   **Workflow for Game Update:**

        1.  Run `mui locate-game` (if game version might have changed).

        2.  Run `mui fetch-vanilla` to get the new base game files.

        3.  Run `mui apply-patch --source-patch-version <previous_game_version>` (or the version your last good patches were for). This will attempt to apply your old patches to the new vanilla files (copied into your working directory, e.g., `<framework_root>/gui/`).

        4.  Manually inspect and resolve any conflicts. `git apply` (used internally) will create `.rej` files for conflicts. Edit your working files (e.g., in `<framework_root>/gui/`) to fix them.

        5.  Once all files are correctly updated for the new game version, run `mui create-patch` to generate new patches against the new vanilla files.

    -   If no specific files are listed, it processes all `tracked_files`.

    -   If `--source-patch-version` is omitted, it defaults to applying patches from the current game version's patch directory.


#### For Dependent Mod Developers (run from dependent mod root)

1.  **`mui distribute`**

    -   Reads `mui_import_config.json` in the current (dependent mod's) directory.

    -   Copies the specified files from the Modular UI Framework (found via `modular_ui_framework_path`) into your mod.

    -   This is the primary command for dependent mod developers to pull in the latest framework files they need.


### File Structure (within `vic3-modular-ui-framework` root)

```
vic3-modular-ui-framework/
├── .envrc                  # For direnv (framework root)
├── gui/                    # Your framework's modified UI files (mod_source_dir)
│   ├── information_panel_bar.gui
│   ├── market_panel.gui
│   └── modular_ui_framework_types.gui
├── mui_config.json         # Main configuration for the tool
├── patches/                # Stores generated .patch files
│   └── 1.6.0/              # Example game version
│       ├── gui/information_panel_bar.gui.patch
│       └── ...
├── tools/
│   ├── .envrc              # For direnv (tools directory)
│   ├── Pipfile             # For mui.py dependencies (e.g., click)
│   ├── Pipfile.lock        # Lock file for dependencies
│   ├── mui                 # Bash wrapper for mui.py
│   └── mui.py              # The Python CLI tool script
└── vanilla_files/          # Stores fetched vanilla game files
    └── 1.6.0/              # Example game version
        ├── gui/information_panel_bar.gui
        └── ...

```

### Troubleshooting (`mui` tool)

-   **`mui: command not found`**:

    -   Ensure `direnv` is installed and you have run `direnv allow .` in the correct directories (framework root and/or dependent mod root).

    -   Check that your `.envrc` files correctly set up the `PATH_add` for the `tools` directory of the framework.

-   **`NameError: name '...' is not defined` (Python error)**:

    -   You might have an incomplete or corrupted `mui.py` script. Ensure you have the latest full version.

-   **`diff: command not found` or `git: command not found`**:

    -   Make sure `diffutils` and `git` are installed and their executable locations are in your system's PATH.

-   **Patching Issues (`apply-patch` or `create-patch`):**

    -   Ensure file paths in `mui_config.json` (`tracked_files`) are correct (relative to the framework repository root).

    -   Verify that `vanilla_files/` for the relevant version contains the correct base game files.

    -   When `apply-patch` reports conflicts, look for `.rej` files next to the target files and manually merge the changes.
