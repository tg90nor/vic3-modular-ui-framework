VIC3_APP_ID="529340"

# Function to find the Steam root directory
find_steam_root() {
    local steam_root=""
    if [ -d "$HOME/.steam/steam" ]; then
        steam_root="$HOME/.steam/steam"
    elif [ -d "$HOME/.local/share/Steam" ]; then
        steam_root="$HOME/.local/share/Steam"
    fi
    echo "$steam_root"
}

# Function to find the game installation directory (e.g., /path/to/Victoria3)
# Returns the base game directory, not including the 'game' subdirectory.
game_install_dir() {
    local app_id="$1"
    local steam_root="$(find_steam_root)"
    local game_path=""

    if [ -z "$steam_root" ]; then
        echo "Error: Steam root directory not found." >&2
        return 1
    fi

    LIBRARY_FOLDERS_VDF="$steam_root/steamapps/libraryfolders.vdf"
    if [ ! -f "$LIBRARY_FOLDERS_VDF" ]; then
        echo "Error: libraryfolders.vdf not found at $LIBRARY_FOLDERS_VDF" >&2
        return 1
    fi

    declare -a library_paths
    library_paths=("$steam_root/steamapps") # Add default library path first

    while IFS= read -r line; do
        library_paths+=("$line")
    done < <(awk -F'"' '/"path"/ {print $4}' "$LIBRARY_FOLDERS_VDF")

    for lib_path in "${library_paths[@]}"; do
        MANIFEST_FILE="$lib_path/steamapps/appmanifest_$app_id.acf"
        if [ -f "$MANIFEST_FILE" ]; then
            GAME_SUBDIR=$(grep -oP '"installdir"\s*"\K[^"]+' "$MANIFEST_FILE")
            if [ -n "$GAME_SUBDIR" ]; then
                game_path="$lib_path/steamapps/common/$GAME_SUBDIR"
                break
            fi
        fi
    done

    if [ -z "$game_path" ]; then
        echo "Error: Game (App ID $app_id) installation directory not found." >&2
        return 1
    fi

    echo "$game_path"
    return 0
}

vic3_version() {
    local gamedir=$(game_install_dir "$VIC3_APP_ID")
    local version_file="$gamedir/caligula_branch.txt"
    if [ -f "$version_file" ]; then
        # Extract the version number from the file
        grep -oP 'release/\K\d+\.\d+(\.\d+)*' "$version_file"
    else
        echo "Error: Version file '$version_file' not found." >&2
        return 1
    fi
}

