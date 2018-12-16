# -*- coding: utf-8 -*-
#      ____________
#   _ /       |    \ ___________ _ _______________ _ ___ _______________
#  /  |    ___/    |   _ __ _  _| |   ___  __ _ __| |   \\    ___  ___ _\
# /   \___/  ______/  | '_ \ || | |__/ _ \/ _` / _` |    \\  / _ \/ _ `/ \
# \       |   o|      | .__/\_, |____\___/\__,_\__,_|    // /_//_/\_, /  /
#  \______\    /______|_|___|__/________________________//______ /___/__/
#          \  /
#           \/

import os
import random
import re
import string
import sys
import time
from html.entities import name2codepoint
import html.parser
import unicodedata
import datetime
from datetime import timedelta
import shutil
import urllib.parse
from functools import partial, wraps
from .. import exc_logger

try:
    import send2trash
except ImportError:
    send2trash = None


def invertmap(obj):
    """
    Invert mapping object preserving type and ordering.
    """
    return obj.__class__(map(reversed, obj.items()))


def random_string(lenght):
    seq = string.ascii_letters + string.digits + string.punctuation
    return "".join(random.choice(seq) for _ in range(lenght))


def chmod(*args):
    try:
        os.chmod(*args)
    except Exception:
        pass

        
# Hotfix UnicodeDecodeError: 'ascii' codec can't decode..
def normalize(value):
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore")


# NOTE: Revert to `decode` in Python 3
def decode(value):
    """
    Encoded string (default to own system encoding) -> unicode string.
    """
    try:
        return str(res)
    except UnicodeEncodeError:
        return normalize(res)


def remove_chars(value, repl):
    """
    Removes all chars in repl from string.
    """
    for char in repl:
        value = value.replace(char, "")
    return value


# def save_path(name):
    # # os.remove some chars
    # if os.name == "nt":
        # return remove_chars(name, '/\\?%*:|"<>')
    # else:
        # return remove_chars(name, '/\\"')


# def save_join(*args):
    # """
    # joins a path, encoding aware.
    # """
    # return fs_encode(
        # os.path.join(*[x if isinstance(x, str) else decode(x) for x in args])
    # )


def truncate(name, length):
    max_trunc = len(name) // 2
    if length > max_trunc:
        raise OSError("File name too long")

    trunc = (len(name) - length) // 3
    return "{}~{}".format(name[: trunc * 2], name[-trunc:])


# TODO: Recheck in 0.6.x
def safepath(value):
    """
    Remove invalid characters and truncate the path if needed.
    """
    if os.name == "nt":
        unt, value = os.path.splitunc(value)
    else:
        unt = ""
    drive, filename = os.path.splitdrive(value)
    filename = os.path.join(
        os.sep if os.path.isabs(filename) else "",
        *list(map(safename, filename.split(os.sep))),
    )
    path = unt + drive + filename

    try:
        if os.name != "nt":
            return

        length = len(path) - 259
        if length < 1:
            return

        dirname, basename = os.path.split(filename)
        name, ext = os.path.splitext(basename)
        path = unt + drive + dirname + truncate(name, length) + ext

    finally:
        return path


def safejoin(*args):
    """
    os.path.join + safepath.
    """
    return safepath(os.path.join(*args))


def safename(value):
    """
    Remove invalid characters.
    """
    repl = '<>:"/\\|?*' if os.name == "nt" else '\0/\\"'
    name = remove_chars(value, repl)
    return name


def compare_time(start, end):
    start = map(int, start)
    end = map(int, end)

    if start == end:
        return True

    now = list(time.localtime()[3:5])

    if start < end:
        if now < end:
            return True

    elif now > start or now < end:
        return True

    return False


def format_time(value):
    dt = datetime.datetime(1, 1, 1) + timedelta(seconds=abs(int(value)))
    days = ("{} days".format(dt.day - 1)) if dt.day > 1 else ""
    tm = ", ".join(
        "{} {}s".format(getattr(dt, attr), attr)
        for attr in ("hour", "minute", "second")
        if getattr(dt, attr)
    )
    return days + (" and " if days and tm else "") + tm


def format_size(value):
    """
    formats size of bytes
    """
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB"):
        if abs(value) < 1 << 10:
            return "{:3.2f} {}".format(value, unit)
        else:
            value >>= 10
    return "{:.2f} {}".format(value, "YiB")


def formatSpeed(speed):
    return format_size(speed) + "/s"


# def freeSpace(folder):
    # if os.name == "nt":
        # import ctypes

        # free_bytes = ctypes.c_ulonglong(0)
        # ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            # ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes)
        # )
        # return free_bytes.value
    # else:
        # s = os.statvfs(folder)
        # return s.f_bsize * s.f_bavail


def free_space(folder):
    if os.name == "nt":
        import ctypes

        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes)
        )
        return free_bytes.value

    else:
        s = os.statvfs(folder)
        return s.f_frsize * s.f_bavail


def uniqify(seq):
    """
    Remove duplicates from list preserving order Originally by Dave Kirby.
    """
    seen = set()
    seen_add = seen.add
    return [x for x in seq if x not in seen and not seen_add(x)]


# def parseFileSize(value, unit=None):  #: returns bytes
    # if not unit:
        # m = re.match(r"(\d*[\.,]?\d+)(.*)", value.strip().lower())
        # if m:
            # traffic = float(m.group(1).replace(",", "."))
            # unit = m.group(2)
        # else:
            # return 0
    # else:
        # if isinstance(value, str):
            # traffic = float(value.replace(",", "."))
        # else:
            # traffic = value

    # # ignore case
    # unit = unit.lower().strip()

    # if unit in ("gb", "gig", "gbyte", "gigabyte", "gib", "g"):
        # traffic *= 1 << 30
    # elif unit in ("mb", "mbyte", "megabyte", "mib", "m"):
        # traffic *= 1 << 20
    # elif unit in ("kb", "kib", "kilobyte", "kbyte", "k"):
        # traffic *= 1 << 10

    # return traffic


# TODO: Change 'trash' to False because send2trash is optional now
def remove(path, trash=True):
    path = encode(path)

    if not exists(path):
        return

    if trash:
        try:
            send2trash.send2trash(path)
        except AttributeError as exc:
            exc_logger.exception(exc)

    elif os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)

    else:
        os.remove(path)


def fixurl(url, unquote=None):
    old = url
    url = urllib.parse.unquote(url)

    if unquote is None:
        unquote = url is old

    url = decode(url)
    try:
        url = url.decode("unicode-escape")
    except UnicodeDecodeError:
        pass

    url = html_unescape(url)
    url = re.sub(r"(?<!:)/{2,}", "/", url).strip().lstrip(".")

    if not unquote:
        url = urllib.parse.quote(url)

    return url
    
    
def parse_name(value, safechar=True):
    path = fixurl(decode(value), unquote=False)
    url_p = urllib.parse.urlparse(path.rstrip("/"))
    name = (
        url_p.path.split("/")[-1]
        or url_p.query.split("=", 1)[::-1][0].split("&", 1)[0]
        or url_p.netloc.split(".", 1)[0]
    )

    name = urllib.parse.unquote(name)
    return safename(name) if safechar else name


def parse_size(value, unit=""):  #: returns bytes
    m = re.match(r"((?:[\d.,]*)\d)\s*([\w^_]*)", str(value).lower())

    if m is None:
        return 0

    if re.match(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?$", m.group(1)):
        size = float(m.group(1).replace(",", ""))

    elif re.match(r"\d+,\d{2}$", m.group(1)):
        size = float(m.group(1).replace(",", "."))

    elif re.match(r"\d+(?:\.\d+)?$", m.group(1)):
        size = float(m.group(1))

    else:
        return 0  #: Unknown format

    unit = (unit.strip().lower() or m.group(2) or "byte")[0]

    if unit == "b":
        return int(size)

    sizeunits = ("b", "k", "m", "g", "t", "p", "e", "z", "y")
    sizemap = {u: i * 10 for i, u in enumerate(sizeunits)}
    magnitude = sizemap[unit]

    i, d = divmod(size, 1)
    integer = int(i) << magnitude
    decimal = int(d * (1 << 10 ** (magnitude // 10)))

    return integer + decimal


def lock(func=None, *decor_args, **decor_kwargs):
    if func is None:
        return partial(lock, *decor_args, **decor_kwargs)

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.lock.acquire(*decor_args, **decor_kwargs)
        try:
            return func(self, *args, **kwargs)
        finally:
            self.lock.release()

    return wrapper


# def fixup(m):
    # text = m.group(0)
    # if text[:2] == "&#":
        # # character reference
        # try:
            # if text[:3] == "&#x":
                # return chr(int(text[3:-1], 16))
            # else:
                # return chr(int(text[2:-1]))
        # except ValueError:
            # pass
    # else:
        # # named entity
        # try:
            # name = text[1:-1]
            # text = chr(name2codepoint[name])
        # except KeyError:
            # pass

    # return text  #: leave as is


def html_unescape(text):
    """
    Removes HTML or XML character references and entities from a text string.
    """
    h = html.parser.HTMLParser()
    return h.unescape(text)