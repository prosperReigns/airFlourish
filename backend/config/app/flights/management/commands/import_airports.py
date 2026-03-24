import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from app.flights.models import Airport


class Command(BaseCommand):
    help = "Import airports from a CSV or JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "file_path",
            type=str,
            help="Path to a CSV or JSON file containing airport data.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file_path"]).expanduser()
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        records = self._load_records(file_path)
        existing_codes = set(Airport.objects.values_list("code", flat=True))
        seen_codes = set()
        airports_to_create = []
        skipped_duplicates = 0

        for record in records:
            code = (record.get("code") or "").strip().upper()
            if not code:
                continue
            if code in existing_codes or code in seen_codes:
                skipped_duplicates += 1
                continue

            city = (record.get("city") or "").strip()
            name = (record.get("name") or "").strip()
            country = (record.get("country") or "").strip()
            if not (city and name and country):
                continue

            airports_to_create.append(
                Airport(code=code, city=city, name=name, country=country)
            )
            seen_codes.add(code)

        Airport.objects.bulk_create(airports_to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(airports_to_create)} airports. "
                f"Skipped {skipped_duplicates} duplicates."
            )
        )

    def _load_records(self, file_path: Path):
        suffix = file_path.suffix.lower()
        if suffix == ".json":
            with file_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                payload = payload.get("airports", [])
            if not isinstance(payload, list):
                raise CommandError("JSON file must contain a list of airports.")
            return payload
        if suffix in {".csv", ".txt"}:
            with file_path.open("r", encoding="utf-8") as handle:
                return list(csv.DictReader(handle))
        raise CommandError("Unsupported file type. Use .csv or .json.")
