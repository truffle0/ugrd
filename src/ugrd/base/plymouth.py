from zenlib.util import unset
from configparser import ConfigParser
from pathlib import Path

PLYMOUTH_CONFIG_FILES = ['/etc/plymouth/plymouthd.conf', '/usr/share/plymouth/plymouthd.defaults']


@unset('plymouth_config')
def find_plymouth_config(self):
    """ Adds the plymouth config files to the build directory """
    self.logger.info("Finding plymouthd.conf")
    for file in PLYMOUTH_CONFIG_FILES:
        plymouth_config = ConfigParser()
        plymouth_config.read(file)
        if plymouth_config.has_section('Daemon') and plymouth_config.has_option('Daemon', 'Theme'):
            self['plymouth_config'] = file
            break
        self.logger.debug("Plymouth config file missing theme option: %s" % file)
    else:
        raise FileNotFoundError('Failed to find plymouthd.conf')


def _process_plymouth_config(self, file):
    """ Checks that the config file is valid """
    self.logger.info("Processing plymouthd.conf: %s" % file)
    plymouth_config = ConfigParser()
    plymouth_config.read(file)
    self['plymouth_theme'] = plymouth_config['Daemon']['Theme']
    self.data['plymouth_config'] = file
    self['dependencies'] = file


def _process_plymouth_theme(self, theme):
    """ Checks that the theme is valid """
    theme_dir = Path('/usr/share/plymouth/themes') / theme
    if not theme_dir.exists():
        raise FileNotFoundError('Theme directory not found: %s' % theme_dir)

    self.data['plymouth_theme'] = theme


def pull_plymouth(self):
    """ Adds plymouth files to dependencies """
    dir_list = [Path('/usr/lib64/plymouth'), Path('/usr/share/plymouth/themes/') / self["plymouth_theme"]]
    self.logger.info("Adding plymouth files to dependencies.")
    for directory in dir_list:
        for file in directory.rglob('*'):
            self['dependencies'] = file


def start_plymouth(self):
    """
    Runs plymouthd
    """
    return ['plymouthd --attach-to-session --pid-file /run/plymouth/pid --mode=boot', 'plymouth show-splash']
