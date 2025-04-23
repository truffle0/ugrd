__version__ = "1.2.0"

from pathlib import Path
from uuid import uuid4
from zenlib.util import colorize as c_
from zenlib.util import unset


@unset("test_kernel")
def find_kernel_path(self):
    """Finds the kernel path for the current system"""
    self.logger.info("Trying to find the kernel path for: %s", c_(self["kernel_version"], "blue"))
    kernel_path = Path(self["_kmod_dir"]) / "vmlinuz"  # try this first
    if not (self["_kmod_dir"] / "vmlinuz").exists():
        for search_dir in ["/boot", "/efi"]:
            for prefix in ["vmlinuz", "kernel", "linux", "bzImage"]:
                kernel_path = Path(search_dir) / f"{prefix}-{self['kernel_version']}"
                if kernel_path.exists():
                    break
            if kernel_path.exists():
                break
        else:
            raise FileNotFoundError("Kernel not found: %s" % self["kernel_version"])

    self.logger.info("Found kernel at: %s", c_(kernel_path, "cyan"))
    self["test_kernel"] = kernel_path


def init_test_vars(self):
    """Initializes the test variables"""
    find_kernel_path(self)
    if not self["test_flag"]:
        self["test_flag"] = uuid4()


def _get_qemu_cmd_args(self, test_image):
    """Returns arguements to run QEMU for the current test configuration."""
    test_initrd = self._get_out_path(self["out_file"])
    self.logger.info("Testing initramfs image: %s", c_(test_initrd, "yellow", bold=True))
    test_rootfs = test_image._get_out_path(test_image["out_file"])
    self.logger.info(
        "Test rootfs image: %s",
        c_(
            test_rootfs,
            "yellow",
        ),
    )
    self.logger.info("Test kernel: %s", c_(self["test_kernel"], "yellow"))
    qemu_args = {
        "-m": self["test_memory"],
        "-cpu": self["test_cpu"],
        "-kernel": self["test_kernel"],
        "-initrd": test_initrd,
        "-serial": "mon:stdio",
        "-append": self["test_cmdline"],
        "-drive": "file=%s,format=raw" % test_rootfs,
    }

    qemu_bools = [f"-{item}" for item in self["qemu_bool_args"]]

    arglist = [f"qemu-system-{self['test_arch']}"] + qemu_bools
    for key, value in qemu_args.items():
        arglist.append(key)
        arglist.append(value)

    return arglist


def get_copy_config_types(self) -> dict:
    """Returns the 'custom_parameters' name, type pairs for config to be copied to the test image"""
    return {key: self["custom_parameters"][key] for key in self["test_copy_config"] if key in self["custom_parameters"]}


def make_test_image(self):
    """Creates a new initramfs generator to create the test image"""
    from ugrd.initramfs_generator import InitramfsGenerator

    kwargs = {
        "logger": self.logger,
        "validate": False,
        "NO_BASE": True,
        "config": None,
        "modules": "ugrd.fs.test_image",
        "out_file": self["test_rootfs_name"],
        "build_dir": self["test_rootfs_build_dir"],
        "custom_parameters": get_copy_config_types(self),
        **{key: self.get(key) for key in self["test_copy_config"] if self.get(key) is not None},
    }

    target_fs = InitramfsGenerator(**kwargs)
    try:
        target_fs.build()
    except (FileNotFoundError, RuntimeError, PermissionError) as e:
        self.logger.error("Test image configuration:\n%s", target_fs)
        raise RuntimeError("Failed to build test rootfs: %s" % e)

    return target_fs


def test_image(self):
    """Runs the test image in QEMU"""
    import re
    from subprocess import Popen, PIPE
    from signal import signal, SIGALRM, alarm
    import unicodedata as unicode

    image = make_test_image(self)
    qemu_cmd = _get_qemu_cmd_args(self, image)

    re_panic = re.compile(r".*---\[ end Kernel panic - .* \]---.*")
    re_ansi = re.compile(r"\x1b\[[\d;]+m")

    # WARN: this timeout approach only works on the assumption that ugRD will
    # *always* run in the main thread, as exceptions raised in signal handlers
    # surface in the main thread
    # See: https://docs.python.org/3/library/signal.html#handlers-and-exceptions
    def timeout(signum, stack):
        raise RuntimeError("Test timeout expired")

    signal(SIGALRM, timeout)

    self.logger.debug("Test config:\n%s", image)
    self.logger.info("Test flag: %s", c_(self["test_flag"], "magenta"))
    self.logger.info("QEMU command: %s", c_(" ".join([str(arg) for arg in qemu_cmd]), bold=True))

    qemu_stdout = []
    with Popen(qemu_cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE, universal_newlines=True) as proc:
        try:
            # Start timeout timer
            alarm(self["test_timeout"])

            self.logger.debug("QEMU output:")
            for line in proc.stdout:
                # Remove ALL ansi sequences and control characters, QEMU has a
                # bad habit of messing with TTY properties when unfiltered
                line = "".join(c for c in re_ansi.sub("", line).strip() if unicode.category(c) != "Cc")
                qemu_stdout.append(line)
                self.logger.debug(line)

                if self["test_flag"] in line:
                    self.logger.info("Test passed!")
                    break

                # detect kernel panic (failed test)
                if re_panic.match(line):
                    panic_time = line.split("]")[0][1:].strip()
                    self.logger.info("Test took: %s", c_(panic_time, "yellow", bold=True, bright=True))
                    raise RuntimeError("Test kernel panic")

        except RuntimeError as err:
            self.logger.error(f"Test failed: {err}")
            self.logger.error(f"QEMU stdout:\n{'\n'.join(qemu_stdout)}")
            raise err

        finally:
            # remove any pending alarms
            alarm(0)

            # Ensure we never leave this block without killing the process
            # empty stdout & stderr, as full pipes can hang the process
            proc.kill()
            _, _ = proc.communicate()
            proc.wait()
