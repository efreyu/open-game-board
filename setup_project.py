import os
import subprocess
import json
import platform
import sys
import shutil
import argparse

# This script is used to build the Godot Engine and generate the project file for the game.
# The script is intended to be run from the root of the project directory.
# The script will clone the Godot Engine repository, build the engine, and generate the project file.
# The script will also copy the custom_build.py file to the Godot Engine repository and set the build mode.
# For more info about compiling Godot Engine editor and template,
# see: https://docs.godotengine.org/en/stable/contributing/development/compiling/introduction_to_the_buildsystem.html
project_name = "open_game_board"
godot_version = "4.2.2-stable"
settings = []

def load_settings():
    project_path = os.getcwd()
    project_settings_path = os.path.join(project_path, 'tools/config/project_config.json')
    with open(project_settings_path) as settings_file:
        settings = json.load(settings_file)

def find_visual_studio_version():
    # Path to vswhere.exe - adjust if necessary
    vswhere_path = r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"

    # Execute vswhere.exe to find the latest Visual Studio installation
    try:
        output = subprocess.check_output([vswhere_path, "-latest", "-format", "json"])
        vs_info = json.loads(output)
        if len(vs_info) > 0:
            # Extract needed information
            installation_version = vs_info[0]["installationVersion"]
            major_version = installation_version.split('.')[0]

            # Map major version to Visual Studio name for CMake
            vs_cmake_name = {
                "17": "Visual Studio 17 2022",
                "16": "Visual Studio 16 2019",
                "15": "Visual Studio 15 2017",
                # Add more mappings as needed
            }.get(major_version, "")

            if vs_cmake_name:
                return vs_cmake_name
            else:
                raise ValueError(f"Unsupported Visual Studio version: {major_version}")
        else:
            raise ValueError("No Visual Studio installation found")
    except subprocess.CalledProcessError as e:
        print(f"Failed to run vswhere.exe: {e}")
        return None
    except FileNotFoundError:
        print(f"vswhere.exe not found at expected location: {vswhere_path}")
        return None


def is_scons_installed():
    try:
        subprocess.check_call(['scons', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_scons():
    print("Installing scons...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'scons'])


def get_os_name():
    # Translate OS and Architecture to Godot build options
    os_name = platform.system().lower()
    if os_name == 'linux':
        return 'linuxbsd'
    elif os_name == 'windows':
        return 'windows'
    elif os_name == 'darwin':
        return 'macos'
    else:
        # todo need to add support for android and ios as well
        return 'unsupported'


def clone_and_build_godot(current_path, target_directory, is_production=False):
    if not os.path.exists(target_directory):
        print("Cloning Godot Engine...")
        subprocess.check_call(['git', 'clone', 'https://github.com/godotengine/godot.git', target_directory])
    os.chdir(target_directory)
    subprocess.check_call(['git', 'checkout', 'master'])
    subprocess.check_call(['git', 'pull'])
    subprocess.check_call(['git', 'checkout', '-f', godot_version])
    subprocess.check_call(['git', 'pull', 'origin', godot_version])

    # Apply custom build options
    target_path = f"{target_directory}/custom.py"
    copy_custom_build_script(f"{current_path}/tools/config/custom_build.py", target_path, is_production)

    # arch, _ = platform.architecture()
    machine_arch = platform.machine()

    # Adjust build command for architecture
    if machine_arch == 'arm64':
        arch = 'arm64'
    else:
        arch = 'x86_64'

    platform_name = get_os_name()
    print(f"Building Godot Engine for {platform_name} ({arch}), this may take a while...")
    cpu_count = os.cpu_count()
    subprocess.check_call(['scons', f'-j{cpu_count}', f'platform={platform_name}',
                           'target=editor', f'arch={arch}',
                           f'{"dev_build=yes" if not is_production else "production=yes"}',
                           f'extra_suffix={project_name}_{godot_version}'])
    subprocess.check_call(['scons', f'-j{cpu_count}', f'platform={platform_name}',
                           f'target={"template_debug" if not is_production else "template_release"}', f'arch={arch}',
                           f'{"dev_build=yes" if not is_production else "production=yes"}',
                           f'extra_suffix={project_name}_{godot_version}'])


def copy_custom_build_script(source_path, target_path, is_production=False):
    # Ensure the target directory exists
    target_dir = os.path.dirname(target_path)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    # Copy the file
    shutil.copyfile(source_path, target_path)
    print(f"File copied from {source_path} to {target_path}")
    # Append the specified line to the end of the file
    with open(target_path, 'a') as file:
        if is_production:
            file.write("\nproduction=\"yes\"")
        else:
            file.write("\nproduction=\"no\"")
    print(f"Appended line to {target_path}")


def get_editor_path(target_directory, is_production=False, symlink=False):
    # base template name - godot.<platform>.<target>[.dev][.double].<arch>[.<extra_suffix>][.<ext>]
    # example: godot.macos.editor.dev.arm64.open_game_board
    os_name = get_os_name()
    machine_arch = platform.machine()
    if machine_arch == 'arm64':
        arch = 'arm64'
    else:
        arch = 'x86_64'
    if symlink:
        editor_name = f"godot.{os_name}.editor.link"
    else:
        editor_name = f"godot.{os_name}.editor{'' if is_production else '.dev'}.{arch}.{project_name}_{godot_version}"
    if os_name == 'windows':
        editor_name += '.exe'

    return os.path.join(target_directory, 'bin', editor_name)


def get_template_path(target_directory, is_production=False, symlink=False):
    # base template name - godot.<platform>.<target>[.dev][.double].<arch>[.<extra_suffix>][.<ext>]
    # example: godot.macos.template_debug.dev.arm64.open_game_board
    os_name = get_os_name()
    machine_arch = platform.machine()
    if machine_arch == 'arm64':
        arch = 'arm64'
    else:
        arch = 'x86_64'
    if symlink:
        template_name = f"godot.{os_name}.template.link"
    else:
        template_name = f"godot.{os_name}.template_{'release' if is_production else 'debug'}{'' if is_production else '.dev'}.{arch}.{project_name}_{godot_version}"
    if os_name == 'windows':
        template_name += '.exe'

    return os.path.join(target_directory, 'bin', template_name)


def check_godot_installed(target_directory, is_production=False):
    if not os.path.exists(os.path.join(target_directory, 'bin')):
        return False
    # search for the Godot executables for the current platform, need to find editor (for pc/mac) and template
    editor_path = get_editor_path(target_directory, is_production)
    template_path = get_template_path(target_directory, is_production)
    if not os.path.exists(editor_path):
        return False
    if not os.path.exists(template_path):
        return False
    return True


def prepare_and_install_godot(is_production=False, symlink=True, reinstall=False):
    home_dir = os.path.expanduser("~")
    godot_engine_path = os.path.join(home_dir, ".godot-engine")
    current_path = os.getcwd()

    # Check if Godot is already installed
    if not reinstall and check_godot_installed(godot_engine_path, is_production):
        print("Godot Engine is already installed.")
    else:
        # Install scons if not present
        if not is_scons_installed():
            install_scons()

        # Clone and build Godot
        clone_and_build_godot(current_path, godot_engine_path, is_production)

    # Create symlink to the godot executable
    if symlink:
        # Assuming the build process creates an executable in the 'bin' directory
        editor_path = get_editor_path(godot_engine_path, is_production)
        editor_path_link = get_editor_path(godot_engine_path, is_production, True)
        template_path = get_template_path(godot_engine_path, is_production)
        template_path_link = get_template_path(godot_engine_path, is_production, True)

        # Creating symlink to the godot executable
        if os.path.exists(editor_path_link) and os.path.islink(editor_path_link):
            os.unlink(editor_path_link)
        if os.path.exists(template_path_link) and os.path.islink(template_path_link):
            os.unlink(template_path_link)
        os.symlink(editor_path, editor_path_link)
        os.symlink(template_path, template_path_link)

        print(f"Godot Engine is ready. Symlink created.")
    else:
        print("Godot Engine is ready. Symlink creation skipped.")


def generate_project_file(mode, is_production=False):
    os_name = platform.system().lower()
    home_dir = os.path.expanduser("~")
    godot_engine_path = os.path.join(home_dir, ".godot-engine")
    editor_path = get_editor_path(godot_engine_path, is_production)
    template_path = get_template_path(godot_engine_path, is_production)
    if mode == 'none':
        print('Skipping project file generation')
        print('Please note that in your manual project you may need to put following cmake arguments manually:')
        print(f'-DCMAKE_BUILD_TYPE={"Release" if is_production else "Debug"}')
        # print(f'-DGODOT_EDITOR_PATH={editor_path}')
        print(f'Godot engine executable located: {editor_path}')
        # print(f'-DGODOT_EDITOR_PATH={template_path}')
        print(f'Godot project template located: {template_path}')
    elif mode == 'vs' and os_name == 'windows':
        vs_version = find_visual_studio_version()
        if vs_version:
            subprocess.check_call(['cmake', '-B', 'build-win', f'-G {vs_version}',
                                   f'-DCMAKE_BUILD_TYPE={"Release" if is_production else "Debug"}',
                                   '-A x64'
                                   ])
        else:
            print("Visual Studio version not found")
    elif mode == 'vscode':
        subprocess.check_call(['cmake', '-B', 'build-vscode',
                               f'-DCMAKE_BUILD_TYPE={"Release" if is_production else "Debug"}'])
    elif mode == 'xcode' and os_name == 'darwin':
        subprocess.check_call(['cmake', '-B', 'build-mac', '-G Xcode',
                               f'-DCMAKE_BUILD_TYPE={"Release" if is_production else "Debug"}'])
    else:
        print(f"Unsupported project file generator: {mode} and OS: {os_name}")


def main():
    # get_settings()
    parser = argparse.ArgumentParser(
        description='Generate project files and install and compile godot engine and templates.')
    parser.add_argument('mode', default='auto', choices=['auto', 'dev', 'production'],
                        help='Build mode (auto, dev, production) (default: auto)')
    parser.add_argument('generate', default='vs', choices=['vs', 'vscode', 'xcode', 'none'],
                        help='Generate project file (vs, vscode, xcode, none), with mode=auto will be ignored (default: vs)')
    parser.add_argument('reinstall', default='none',
                        help='Rebuild the godot engine and template, this might be required after getting changes in godot modules')
    args = parser.parse_args()
    project_path = os.getcwd()
    reinstall = False
    if args.reinstall == 'true':
        reinstall = True
    if args.mode == 'auto':
        prepare_and_install_godot(False, True, reinstall)
        os.chdir(project_path)
        generate_project_file(args.generate, False)
    elif args.mode == 'dev':
        prepare_and_install_godot(False, True, reinstall)
        os.chdir(project_path)
        generate_project_file(args.generate, False)
    elif args.mode == 'production':
        prepare_and_install_godot(True, True, reinstall)
        os.chdir(project_path)
        generate_project_file(args.generate, True)


if __name__ == "__main__":
    main()
