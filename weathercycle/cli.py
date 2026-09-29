"""命令行入口：跑天气样例。"""

import argparse

from .cycle import TABLE, speed_modifier, weight_sum


def build_parser():
    parser = argparse.ArgumentParser(prog="weather-cycle", description="天气循环")
    parser.add_argument("--sample", default="table", help="table / modifier")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.sample == "table":
        for state in sorted(TABLE):
            print("state=%s sum=%.2f" % (state, weight_sum(state)))
    elif args.sample == "modifier":
        print("rain_modifier=%.2f snow_modifier=%.2f" % (speed_modifier("rain"), speed_modifier("snow")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
