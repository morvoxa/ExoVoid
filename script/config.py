#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess

try:
    import termios
    import tty
except ImportError:
    termios = None
    tty = None


class ExoInstaller:
    class Colors:
        HEADER = "\033[95m"
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        RED = "\033[91m"
        BLUE = "\033[94m"
        ENDC = "\033[0m"
        BOLD = "\033[1m"

    def __init__(self):
        self.config_dir = os.path.expanduser("~/.config/")
        self.source_dir = os.path.expanduser("~/.cache/Exo/")
        self.dry_run = False

    # ======================
    # Core
    # ======================

    def run(self):
        self.print_header("EXO INSTALLER")
        print(f"{self.Colors.BLUE}This installer will set up Exo configs in your home directory.{self.Colors.ENDC}")
        print(f"{self.Colors.BLUE}Target config directory: {self.config_dir}{self.Colors.ENDC}")
        self.full_install()

    def run_command(self, cmd, **kwargs):
        if self.dry_run:
            print(
                f"{self.Colors.YELLOW}[DRY RUN]{self.Colors.ENDC} Would execute: {' '.join(cmd)}"
            )
            return subprocess.CompletedProcess(cmd, 0)

        try:
            return subprocess.run(cmd, check=True, **kwargs)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"{self.Colors.RED}[ERROR]{self.Colors.ENDC} Command failed: {e}")
            return None

    # ======================
    # UI
    # ======================

    def print_header(self, title):
        line = "=" * 60
        print(f"\n{self.Colors.HEADER}{self.Colors.BOLD}{line}{self.Colors.ENDC}")
        print(f"{self.Colors.HEADER}{self.Colors.BOLD} {title.center(58)} {self.Colors.ENDC}")
        print(f"{self.Colors.HEADER}{self.Colors.BOLD}{line}{self.Colors.ENDC}\n")

    def get_user_choice(self, prompt, options):
        if termios and tty:
            try:
                print(
                    f"{self.Colors.YELLOW}{prompt}{self.Colors.ENDC}",
                    end="",
                    flush=True,
                )
                fd = sys.stdin.fileno()
                old = termios.tcgetattr(fd)
                try:
                    tty.setraw(fd)
                    while True:
                        c = sys.stdin.read(1).lower()
                        if c in options:
                            print(c)
                            return c
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
            except termios.error:
                pass

        while True:
            c = input(
                f"{self.Colors.YELLOW}{prompt}{self.Colors.ENDC}"
            ).lower()
            if c in options:
                return c
            print(f"{self.Colors.RED}Invalid input. Please choose one of: {', '.join(options)}{self.Colors.ENDC}")

    # ======================
    # Desktop Configs
    # ======================

    def install_desktop_configs(self, desktop_env):
        self.print_header("DESKTOP CONFIGURATION")

        if desktop_env in ["niri", "both"]:
            self._copy_config(
                "niri",
                "config.kdl",
                "exodefaults/config.kdl",
            )

        if desktop_env in ["hyprland", "both"]:
            self._copy_config(
                "hypr",
                "hyprland.conf",
                "exodefaults/hyprland.conf",
            )

    def _copy_config(self, folder, filename, source_rel):
        print(f"{self.Colors.BLUE}→ Installing config for:{self.Colors.ENDC} {folder}")
        dest_dir = os.path.join(self.config_dir, folder)
        os.makedirs(dest_dir, exist_ok=True)

        src = os.path.join(self.source_dir, source_rel)
        dest = os.path.join(dest_dir, filename)

        if os.path.exists(dest):
            print(f"{self.Colors.YELLOW}[WARNING]{self.Colors.ENDC} {dest} already exists.")
            choice = self.get_user_choice(
                "Choose action: Backup (b), Overwrite (o), Skip (s): ",
                ["b", "o", "s"],
            )

            if choice == "b":
                shutil.copy2(dest, dest + ".bak")
                print(f"{self.Colors.GREEN}Backup created:{self.Colors.ENDC} {dest}.bak")
            elif choice == "s":
                print(f"{self.Colors.YELLOW}Skipped:{self.Colors.ENDC} {dest}")
                return

        shutil.copy2(src, dest)
        print(f"{self.Colors.GREEN}Installed:{self.Colors.ENDC} {dest}")

    # ======================
    # Final Setup
    # ======================

    def final_setup(self):
        self.print_header("FINAL SETUP")

        wallpaper_src = os.path.join(
            self.source_dir, "exodefaults", "default_wallpaper.png"
        )
        wallpaper_dir = os.path.expanduser("~/Pictures/Wallpapers")
        os.makedirs(wallpaper_dir, exist_ok=True)

        wallpaper_dest = os.path.join(wallpaper_dir, "default.png")
        if not os.path.exists(wallpaper_dest):
            shutil.copyfile(wallpaper_src, wallpaper_dest)
            print(f"{self.Colors.GREEN}Wallpaper installed:{self.Colors.ENDC} {wallpaper_dest}")
        else:
            print(f"{self.Colors.YELLOW}Wallpaper already exists:{self.Colors.ENDC} {wallpaper_dest}")

        ignis_dir = os.path.join(self.config_dir, "ignis")
        user_settings = os.path.join(ignis_dir, "user_settings.json")

        print(f"\n{self.Colors.BLUE}Generating initial color scheme (Matugen)...{self.Colors.ENDC}")
        if shutil.which("matugen"):
            cmd = ["matugen", "image", wallpaper_dest]
            result = self.run_command(cmd)

            if result is None or (
                hasattr(result, "returncode") and result.returncode != 0
            ):
                print(f"{self.Colors.RED}[FAILED]{self.Colors.ENDC} Matugen color generation failed.")
            else:
                print(f"{self.Colors.GREEN}[SUCCESS]{self.Colors.ENDC} Color scheme generated.")
        else:
            print(f"{self.Colors.RED}[SKIPPED]{self.Colors.ENDC} Matugen not found in PATH.")

        if not os.path.exists(user_settings):
            os.makedirs(ignis_dir, exist_ok=True)
            with open(user_settings, "w") as f:
                f.write("{}")
            print(f"{self.Colors.GREEN}Created default Ignis user settings.{self.Colors.ENDC}")

        preview_src = os.path.join(
            self.source_dir, "exodefaults", "preview-colors.scss"
        )
        preview_dest = os.path.join(
            ignis_dir, "styles", "preview-colors.scss"
        )

        if not os.path.exists(preview_dest):
            os.makedirs(os.path.dirname(preview_dest), exist_ok=True)
            shutil.copyfile(preview_src, preview_dest)
            print(f"{self.Colors.GREEN}Preview color stylesheet installed.{self.Colors.ENDC}")

    # ======================
    # Full Install
    # ======================

    def full_install(self):
        self.print_header("FULL INSTALLATION")

        for folder in ["ignis", "matugen"]:
            src = os.path.join(self.source_dir, folder)
            dest = os.path.join(self.config_dir, folder)

            print(f"{self.Colors.BLUE}Processing:{self.Colors.ENDC} {folder}")

            if os.path.exists(dest):
                print(f"{self.Colors.YELLOW}[EXISTS]{self.Colors.ENDC} {dest}")
                choice = self.get_user_choice(
                    "Action: Backup (b), Overwrite (o), Quit (q): ",
                    ["b", "o", "q"],
                )

                if choice == "b":
                    shutil.move(dest, dest + "-backup")
                    print(f"{self.Colors.GREEN}Backup created:{self.Colors.ENDC} {dest}-backup")
                elif choice == "o":
                    shutil.rmtree(dest)
                    print(f"{self.Colors.YELLOW}Existing directory removed.{self.Colors.ENDC}")
                else:
                    print(f"{self.Colors.RED}Installation aborted by user.{self.Colors.ENDC}")
                    sys.exit(0)

            shutil.copytree(src, dest)
            print(f"{self.Colors.GREEN}Installed:{self.Colors.ENDC} {dest}\n")

        self.install_desktop_configs("both")
        self.final_setup()
        print(f"\n{self.Colors.GREEN}{self.Colors.BOLD}✔ Installation complete. Enjoy Exo!{self.Colors.ENDC}")


# ======================
# Entry
# ======================

if __name__ == "__main__":
    if os.geteuid() == 0:
        print("Do not run this script as root.")
        sys.exit(1)

    ExoInstaller().run()

