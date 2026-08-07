from __future__ import annotations
import argparse
import sys
from .config import Config
from .data.prepare import prepare
from .data.validate import validate_processed


def _cfg_from_args(a) -> Config:
    over = {}
    for k in ("raw_dir", "processed_dir", "dataset_yaml", "split_dir"):
        v = getattr(a, k, None)
        if v:
            over[k] = v
    return Config.load(getattr(a, "config", None), **over)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(
        prog="plate_detect",
        epilog="Global flags follow the subcommand, e.g. plate_detect check --dry-run --processed-dir DIR",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    for name in ("prepare", "train", "eval", "export", "check"):
        sp = sub.add_parser(name)
        sp.add_argument("--config")
        sp.add_argument("--dry-run", action="store_true")
        sp.add_argument("--raw-dir", dest="raw_dir")
        sp.add_argument("--processed-dir", dest="processed_dir")
        sp.add_argument("--dataset-yaml", dest="dataset_yaml")
        sp.add_argument("--split-dir", dest="split_dir")

    a = p.parse_args(argv)
    cfg = _cfg_from_args(a)

    if a.dry_run:
        print(f"[dry-run] cmd={a.cmd} raw={cfg.raw_dir} processed={cfg.processed_dir} "
              f"models=yolov8n,yolo26n seeds={cfg.seeds}")
        return 0

    if a.cmd == "prepare":
        summary = prepare(cfg)
        print(f"prepared: {summary}")
        return 0
    if a.cmd == "check":
        errs = validate_processed(cfg.processed_dir, cfg.num_classes)
        if errs:
            print("INVALID:\n  " + "\n  ".join(errs)); return 1
        print("data-contract OK"); return 0
    if a.cmd in ("train", "eval", "export"):
        print(f"'{a.cmd}' runs on Colab GPU via notebooks/train-plate-det.ipynb")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
