from django.core.management.base import BaseCommand

from tasks.models import Service

# Mirrors shorolikoron-flutter/scripts/services_seed.json (the old Firestore
# seed data), now seeded straight into Postgres instead.
SERVICES = [
    {"title": "Hall Office", "color_hex": "#2352CC", "order": 0},
    {"title": "Survey Team", "color_hex": "#2352CC", "order": 1},
    {"title": "Advocate/Court", "color_hex": "#2352CC", "order": 2},
    {"title": "Media Ad.", "color_hex": "#2352CC", "order": 3},
    {"title": "Pick & Drop", "color_hex": "#2352CC", "order": 4},
    {"title": "Exclusive Representative Hiring", "color_hex": "#2352CC", "order": 5},
    {"title": "Customised Purchasing", "color_hex": "#2352CC", "order": 6},
    {"title": "Education Board", "color_hex": "#2352CC", "order": 7},
    {"title": "NU Documents Processing", "color_hex": "#2352CC", "order": 8},
    {"title": "Affiliated College Service", "color_hex": "#2352CC", "order": 9},
    {"title": "Bank Draft/Application", "color_hex": "#2352CC", "order": 10},
    {"title": "Medicine Courier/Collection", "color_hex": "#2352CC", "order": 11},
    {"title": "Private University Student", "color_hex": "#2352CC", "order": 12},
    {"title": "Free Consulting/Info Support", "color_hex": "#2352CC", "order": 13},
    {"title": "Certificate/Mark", "color_hex": "#2352CC", "order": 14},
    {"title": "Register Building", "color_hex": "#2352CC", "order": 15},
    {"title": "NU/District rep.", "color_hex": "#2352CC", "order": 16},
    {"title": "Info Collectig", "color_hex": "#2352CC", "order": 17},
    {"title": "Doc Correction", "color_hex": "#2352CC", "order": 18},
    {"title": "Affidavit", "color_hex": "#2352CC", "order": 19},
    {"title": "Medicine Courier", "color_hex": "#2352CC", "order": 20},
    {"title": "Study Mat. courier/DHL,Fedex", "color_hex": "#2352CC", "order": 21},
    {"title": "Department Office", "color_hex": "#2352CC", "order": 22},
    {"title": "WES bank Pay", "color_hex": "#2352CC", "order": 23},
    {"title": "Attestation DU", "color_hex": "#2352CC", "order": 24},
    {"title": "Ministry Attestation", "color_hex": "#2352CC", "order": 25},
    {"title": "Drop Shipping", "color_hex": "#2352CC", "order": 26},
    {"title": "Doc/Parcel Delivery", "color_hex": "#2352CC", "order": 27},
    {"title": "Medical Rep.", "color_hex": "#2352CC", "order": 28},
    {"title": "Application & Payment", "color_hex": "#2352CC", "order": 29},
    {"title": "Representative", "color_hex": "#2352CC", "order": 30},
    {"title": "In Campus", "color_hex": "#2352CC", "order": 31},
    {"title": "Coordinator", "color_hex": "#2352CC", "order": 32},
    {"title": "Purchasing", "color_hex": "#2352CC", "order": 33},
    {"title": "Migration Certificate", "color_hex": "#2352CC", "order": 34},
    {"title": "MOI & Testimonial", "color_hex": "#2352CC", "order": 35},
    {"title": "Transcript Section", "color_hex": "#2352CC", "order": 36},
    {"title": "Partly Assist.", "color_hex": "#2352CC", "order": 37},
    {"title": "7 college", "color_hex": "#2352CC", "order": 38},
    {"title": "Out of Dhaka city", "color_hex": "#2352CC", "order": 39},
    {"title": "BUET/Medical", "color_hex": "#2352CC", "order": 40},
]


class Command(BaseCommand):
    help = "Seeds (or updates) the Service catalog. Safe to re-run — upserts by title."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0
        for entry in SERVICES:
            _, created = Service.objects.update_or_create(
                title=entry["title"],
                defaults={"color_hex": entry["color_hex"], "order": entry["order"]},
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(SERVICES)} services ({created_count} created, {updated_count} updated)."
        ))
