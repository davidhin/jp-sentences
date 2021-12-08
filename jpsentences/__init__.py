"""Set up project paths."""
import hashlib
import inspect
import os
from datetime import datetime
from multiprocessing import Pool
from pathlib import Path

import pandas as pd
from tqdm import tqdm


def project_dir() -> Path:
    """Get project path."""
    return Path(__file__).parent.parent


def storage_dir() -> Path:
    """Get storage path."""
    storage = os.getenv("SINGSTORAGE")
    if storage:
        return Path(storage) / "storage"
    return Path(__file__).parent.parent / "storage"


def external_dir() -> Path:
    """Get storage external path."""
    path = storage_dir() / "external"
    Path(path).mkdir(exist_ok=True, parents=True)
    return path


def interim_dir() -> Path:
    """Get storage interim path."""
    path = storage_dir() / "interim"
    Path(path).mkdir(exist_ok=True, parents=True)
    return path


def processed_dir() -> Path:
    """Get storage processed path."""
    path = storage_dir() / "processed"
    Path(path).mkdir(exist_ok=True, parents=True)
    return path


def outputs_dir() -> Path:
    """Get output path."""
    path = storage_dir() / "outputs"
    Path(path).mkdir(exist_ok=True, parents=True)
    return path


def cache_dir() -> Path:
    """Get storage cache path."""
    path = storage_dir() / "cache"
    Path(path).mkdir(exist_ok=True, parents=True)
    return path


def get_dir(path) -> Path:
    """Get path, if exists. If not, create it."""
    Path(path).mkdir(exist_ok=True, parents=True)
    return path


def debug(msg, noheader=False, sep="\t"):
    """Print to console with debug information."""
    caller = inspect.stack()[1]
    file_name = caller.filename
    ln = caller.lineno
    now = datetime.now()
    time = now.strftime("%m/%d/%Y - %H:%M:%S")
    if noheader:
        print("\t\x1b[94m{}\x1b[0m".format(msg), end="")
        return
    print(
        '\x1b[40m[{}] File "{}", line {}\x1b[0m\n\t\x1b[94m{}\x1b[0m'.format(
            time, file_name, ln, msg
        )
    )


def hashstr(s):
    """Hash a string."""
    return int(hashlib.sha1(s.encode("utf-8")).hexdigest(), 16) % (10 ** 8)


def dfmp(df, function, columns=None, ordr=True, workers=6, cs=10, desc="Run: "):
    """Parallel apply function on dataframe.

    Example:
    def asdf(x):
        return x
    dfmp(list(range(10)), asdf, ordr=False, workers=6, cs=1)
    """
    if isinstance(columns, str):
        items = df[columns].tolist()
    elif isinstance(columns, list):
        items = df[columns].to_dict("records")
    elif isinstance(df, pd.DataFrame):
        items = df.to_dict("records")
    elif isinstance(df, list):
        items = df
    else:
        raise ValueError("First argument of dfmp should be pd.DataFrame or list.")

    processed = []
    desc = f"({workers} Workers) {desc}"
    with Pool(processes=workers) as p:
        map_func = getattr(p, "imap" if ordr else "imap_unordered")
        for ret in tqdm(map_func(function, items, cs), total=len(items), desc=desc):
            processed.append(ret)
    return processed


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]
