"""Command-line interface for the no-website outreach pipeline.

Subcommands:
  discover  query -> leads.csv (no-website businesses only)
  draft     leads.csv -> personalized subject/body columns
  send      leads.csv -> outreach (DRY-RUN BY DEFAULT)
  pipeline  discover then draft
"""

from __future__ import annotations

import argparse
import logging
import sys

DEFAULT_LEADS = "data/leads.csv"
DEFAULT_SUPPRESSION = "data/suppression.csv"


def _add_leads_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument("--leads", default=DEFAULT_LEADS, help="path to leads CSV")


def _add_geo_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--lat", type=float, help="location bias center latitude")
    p.add_argument("--lng", type=float, help="location bias center longitude")
    p.add_argument("--radius-m", type=float, help="location bias radius (meters)")
    p.add_argument("--max-pages", type=int, default=3, help="max result pages")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="no-website-outreach",
        description="Find no-website businesses, draft and (guardedly) send outreach.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("discover", help="find businesses with no website")
    d.add_argument("query", help="text search query, e.g. 'plumbers in Austin TX'")
    _add_geo_args(d)
    _add_leads_arg(d)

    dr = sub.add_parser("draft", help="generate personalized drafts for leads")
    _add_leads_arg(dr)

    s = sub.add_parser("send", help="send drafts (DRY-RUN by default)")
    _add_leads_arg(s)
    s.add_argument("--suppression", default=DEFAULT_SUPPRESSION)
    group = s.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=None,
        help="print planned sends, send nothing (default)",
    )
    group.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        help="actually send (requires DRY_RUN=false config + legal sign-off)",
    )

    pl = sub.add_parser("pipeline", help="discover then draft")
    pl.add_argument("query")
    _add_geo_args(pl)
    _add_leads_arg(pl)

    return parser


def _location(args) -> tuple[float, float] | None:
    lat = getattr(args, "lat", None)
    lng = getattr(args, "lng", None)
    if lat is not None and lng is not None:
        return (lat, lng)
    return None


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)

    # Imported lazily so --help works without external deps configured.
    from . import discover, personalize, pipeline, send

    if args.command == "discover":
        businesses, added = discover.discover_to_csv(
            args.query,
            args.leads,
            location=_location(args),
            radius_m=args.radius_m,
            max_pages=args.max_pages,
        )
        print(
            f"discovered {len(businesses)} no-website businesses, "
            f"{added} new -> {args.leads}"
        )
    elif args.command == "draft":
        drafted = personalize.personalize_csv(args.leads)
        print(f"drafted {drafted} emails -> {args.leads}")
    elif args.command == "send":
        stats = send.send_pipeline(args.leads, args.suppression, dry_run=args.dry_run)
        print(stats)
    elif args.command == "pipeline":
        stats = pipeline.run(
            args.query,
            args.leads,
            location=_location(args),
            radius_m=args.radius_m,
            max_pages=args.max_pages,
        )
        print(stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
