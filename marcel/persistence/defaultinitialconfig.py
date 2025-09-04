CONFIG = '''from marcel.builtin import *

COLOR_EXT_IMAGE = Color(3, 0, 2, BOLD)
COLOR_EXT_SOURCE = Color(0, 3, 4, BOLD)

COLOR_SCHEME.file_file = Color(5, 5, 5, BOLD)
COLOR_SCHEME.file_dir = Color(0, 2, 3, BOLD)
COLOR_SCHEME.file_link = Color(4, 2, 0, BOLD)
COLOR_SCHEME.file_executable = Color(0, 4, 0, BOLD)
COLOR_SCHEME.file_extension = {
    'jpg': COLOR_EXT_IMAGE,
    'jpeg': COLOR_EXT_IMAGE,
    'png': COLOR_EXT_IMAGE,
    'mov': COLOR_EXT_IMAGE,
    'avi': COLOR_EXT_IMAGE,
    'gif': COLOR_EXT_IMAGE,
    'py': COLOR_EXT_SOURCE,
    'c': COLOR_EXT_SOURCE,
    'c++': COLOR_EXT_SOURCE,
    'cpp': COLOR_EXT_SOURCE,
    'cxx': COLOR_EXT_SOURCE,
    'h': COLOR_EXT_SOURCE,
    'java': COLOR_EXT_SOURCE,
    'php': COLOR_EXT_SOURCE
}
COLOR_SCHEME.error = Color(5, 5, 0)
COLOR_SCHEME.process_pid = Color(0, 3, 5, BOLD)
COLOR_SCHEME.process_ppid = Color(0, 2, 4, BOLD)
COLOR_SCHEME.process_status = Color(3, 1, 0, BOLD)
COLOR_SCHEME.process_user = Color(0, 2, 2, BOLD)
COLOR_SCHEME.process_command = Color(3, 2, 0, BOLD)
COLOR_SCHEME.help_reference = Color(5, 3, 0)
COLOR_SCHEME.help_bold = Color(5, 4, 1, BOLD)
COLOR_SCHEME.help_italic = Color(5, 5, 2, ITALIC)
COLOR_SCHEME.help_name = Color(4, 1, 0)
COLOR_SCHEME.history_id = Color(0, 3, 5, BOLD)
COLOR_SCHEME.history_command = Color(4, 3, 0, BOLD)
COLOR_SCHEME.color_scheme_key = Color(2, 4, 0)
COLOR_SCHEME.color_scheme_value = Color(0, 3, 4)

set_prompt(
    Color(0, 5, 5, BOLD),
    'M ',
    Color(0, 2, 3, BOLD),
    MARCEL_VERSION,
    ' ',
    Color(0, 4, 4, BOLD),
    lambda: f'{WORKSPACE} ' if WORKSPACE else '',
    Color(1, 3, 2, BOLD),
    USER,
    '@',
    HOST,
    ' ',
    Color(2, 5, 4, BOLD),
    lambda: (PROMPT_DIR),
    '$ ')

INTERACTIVE_EXECUTABLES = [
    'emacs',
    'less',
    'man',
    'more',
    'psql',
    'top',
    'vi',
    'vim'
]
'''