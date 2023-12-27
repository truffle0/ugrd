#!/usr/bin/env python

from ugrd.initramfs_generator import InitramfsGenerator
from zenlib.logging import ColorLognameFormatter

from argparse import ArgumentParser
from importlib.metadata import version
import logging


def main():
    argparser = ArgumentParser(prog='ugrd',
                               description='MicrogRAM disk initramfs generator')

    argparser.add_argument('-d', '--debug', action='store_true', help='Debug mode.')
    argparser.add_argument('-dd', '--verbose', action='store_true', help='Verbose debug mode.')

    argparser.add_argument('--build-logging', action='store_true', help='Enable additional build logging.')
    argparser.add_argument('--no-build-logging', action='store_true', help='Disable additional build logging.')

    argparser.add_argument('--log-file', action='store', help='Log file location.')

    argparser.add_argument('-v', '--version', action='store_true', help='Print the version and exit.')

    # Add arguments for dracut compatibility
    argparser.add_argument('-c', '--config', action='store', help='Config file location.')
    argparser.add_argument('--kver', action='store', help='Set the kernel version.')

    argparser.add_argument('--clean', action='store_true', help='Enable build directory cleaning.')
    argparser.add_argument('--no-clean', action='store_true', help='Disable build directory cleaning.')

    argparser.add_argument('--validate', action='store_true', help='Enable config validation.')
    argparser.add_argument('--no-validate', action='store_true', help='Disable config validation.')

    argparser.add_argument('--hostonly', action='store_true', help='Enable hostonly mode, required for automatic kmod detection.')
    argparser.add_argument('--no-hostonly', action='store_true', help='Disable hostonly mode.')

    # Add arguments for auto-kmod detection
    argparser.add_argument('--lspci', action='store_true', help='Use lspci to auto-detect kmods')
    argparser.add_argument('--lsmod', action='store_true', help='Use lsmod to auto-detect kmods')

    # Add argument for firmware inclusion
    argparser.add_argument('--firmware', action='store_true', help='Include firmware files found with modinfo.')
    argparser.add_argument('--no-firmware', action='store_true', help='Exclude firmware files.')

    # Add argument for autodecting the root partition
    argparser.add_argument('--autodetect-root', action='store_true', help='Autodetect the root partition.')
    argparser.add_argument('--no-autodetect-root', action='store_true', help='Do not autodetect the root partition.')

    # Add the argument for the output file
    argparser.add_argument('output_file', action='store', help='Output file location', nargs='?')

    # Print the final config_dict
    argparser.add_argument('--print-config', action='store_true', help='Print the final config dict.')

    args = argparser.parse_args()

    if args.version:
        print(f"{__package__} {version(__package__)}")
        exit(0)

    # Set the initial logger debug level based on the args, set the format string based on the debug level
    logger = logging.getLogger()
    if args.verbose:
        logger.setLevel(5)
        formatter = ColorLognameFormatter('%(levelname)s | %(name)-42s | %(message)s')
    elif args.debug:
        logger.setLevel(10)
        formatter = ColorLognameFormatter('%(levelname)s | %(name)-42s | %(message)s')
    else:
        logger.setLevel(20)
        formatter = ColorLognameFormatter()

    if args.log_file:
        handler = logging.FileHandler(args.log_file)
        logger.addHandler(handler)
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Pass the logger to the generator
    kwargs = {'logger': logger}

    # Set config toggles
    for toggle in ['validate', 'hostonly', 'firmware', 'autodetect_root', 'clean', 'build_logging']:
        if arg := getattr(args, f"no_{toggle}"):
            kwargs[toggle] = False

    for config, arg in {'clean': 'clean',
                        'kernel_version': 'kver',
                        'kmod_autodetect_lspci': 'lspci',
                        'kmod_autodetect_lsmod': 'lsmod',
                        'autodetect_root': 'autodetect_root',
                        'validate': 'validate',
                        'hostonly': 'hostonly',
                        'build_logging': 'build_logging',
                        'config': 'config',
                        'out_file': 'output_file'}.items():
        if arg := getattr(args, arg):
            kwargs[config] = arg

    logger.debug(f"Using the following kwargs: {kwargs}")

    generator = InitramfsGenerator(**kwargs)
    try:
        generator.build()
    except Exception as e:
        logger.info("Dumping config dict:\n")
        print(generator.config_dict)
        logger.error(e, exc_info=True)
        exit(1)

    if args.print_config:
        print(generator.config_dict)


if __name__ == '__main__':
    main()

