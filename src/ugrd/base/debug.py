__author__ = "desultory"
__version__ = "1.3.1"

from zenlib.util import contains, colorize
from ugrd import AutodetectError, ValidationError

EXPECTED_EDITORS = { "nano", "vim", "vi", "emacs" }

def detect_editor(self) -> None:
    from os import environ
    editor = self.get("editor") or environ.get("EDITOR") or "nano"
    
    self.logger.info("[debug] Using editor: %s" % colorize(editor, "cyan"))
    
    # setting value will automatically call the hook to validate the path
    # reraising to tell the user it's the editor config to help narrow down the issue
    try:
        self["binaries"] = editor
    except AutodetectError:
        raise AutodetectError("Failed to locate editor binary: %s" % colorize(editor, "cyan"))

    # Send a warning if the editor it's a common one, but still use it if it exists
    if editor not in EXPECTED_EDITORS:
       if self.get("validate") and not self.get("no_validate_editor"):
           raise ValidationError("Use of unrecognised editor %s with validation enabled" % colorize(editor, "cyan"))
       else:
           self.logger.warning("Editor binary not recognised, can be overridden with 'editor' in config or EDITOR in environment if incorrect, otherwise can be disregarded.")



def start_shell(self) -> str:
    """Start a bash shell at the start of the initramfs."""
    return [
        "if ! check_var debug; then",
        '    ewarn "The debug module is enabled, but debug is not set enabled"',
        "    return",
        "fi",
        'einfo "Starting debug shell"',
        "bash -l",
    ]


@contains("start_shell", "Not enabling the debug shell, as the start_shell option is not set.", log_level=30)
def enable_debug(self) -> str:
    """Enable debug mode."""
    return "setvar debug 1"
