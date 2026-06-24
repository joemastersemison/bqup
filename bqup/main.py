"""bqup - backing up your BigQuery non-data

Usage:
  bqup [-p PROJECT_ID] [-d TARGET_DIR] [-fvxr] [-e REGEX] [-c DAYS]

Options:
  -p PROJECT_ID, --project PROJECT_ID  Project ID to load. If unspecified, defaults to current project in configuration.
  -d TARGET_DIR, --dir TARGET_DIR      The target directory where the project will be written. Defaults to current timestamp.
  -f --force                           Overwrite target directory if it exists.
  -v --verbose                         Print a summary of the loaded project.
  -x --schema                          Export table schemata as json.
  -r --routine                         Include routines in export.
  -e REGEX, --regex REGEX              Regex pattern to filter datasets to be exported.
  -c DAYS, --changed-since DAYS        Only back up views/tables/routines modified within the past DAYS days.
"""
import os
from datetime import datetime
from docopt import docopt
from bqup.changes import parse_changed_since
from bqup.project import Project


def main():
    args = docopt(__doc__)

    target_dir = args['--dir'] or datetime.isoformat(datetime.now())
    force = args['--force']

    if (not force) and os.path.exists(target_dir):
        print("Target directory already exists. Consider running with -f.")
        exit()

    changed_since_days = parse_changed_since(args['--changed-since'])

    project_id = args['--project']
    print(f"Loading {project_id or 'default project'}...")
    if changed_since_days is not None:
        print(f"Restricting backup to objects modified within the past {changed_since_days} day(s).")
    p = Project(project_id or None, args['--schema'], args['--routine'], args['--regex'], changed_since_days)

    if args['--verbose']:
        p.print_info()

    print(f"Loaded {p.project_id}.")

    print(f"Exporting {p.project_id} to {target_dir}...")
    p.export(target_dir, force=force)
    print(f"Project {p.project_id} exported to {target_dir}.")


if __name__ == "__main__":
    main()
