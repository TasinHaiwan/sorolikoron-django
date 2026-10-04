from django.core.management.base import BaseCommand

from tasks.models import Service

# Mirrors shorolikoron-flutter/scripts/services_seed.json (the old Firestore
# seed data), now seeded straight into Postgres instead.
#
# icon_slug values are Tabler Icons (tabler.io/icons, MIT licensed) outline
# icon filenames without the .svg extension — see
# tasks/static/service_icons/README.md for how to add more.
SERVICES = [
    {"title": "Hall Office", "color_hex": "#2352CC", "icon_slug": "building", "order": 0,
     "description": "On-campus hall office visits and paperwork handled on your behalf."},
    {"title": "Survey Team", "color_hex": "#2352CC", "icon_slug": "clipboard-list", "order": 1,
     "description": "Site surveys and on-ground data collection by our field team."},
    {"title": "Advocate/Court", "color_hex": "#2352CC", "icon_slug": "scale", "order": 2,
     "description": "Court visits and advocate liaison for your legal paperwork."},
    {"title": "Media Ad.", "color_hex": "#2352CC", "icon_slug": "ad-2", "order": 3,
     "description": "Newspaper and media advertisement placement, handled end to end."},
    {"title": "Pick & Drop", "color_hex": "#2352CC", "icon_slug": "truck-delivery", "order": 4,
     "description": "Local pickup and drop-off for documents or items, door to door."},
    {"title": "Exclusive Representative Hiring", "color_hex": "#2352CC", "icon_slug": "briefcase", "order": 5,
     "description": "Hire a dedicated representative for your ongoing errands."},
    {"title": "Customised Purchasing", "color_hex": "#2352CC", "icon_slug": "shopping-cart", "order": 6,
     "description": "We buy items on your list and deliver them to you."},
    {"title": "Education Board", "color_hex": "#2352CC", "icon_slug": "school", "order": 7,
     "description": "Education board visits for forms, certificates, and verification."},
    {"title": "NU Documents Processing", "color_hex": "#2352CC", "icon_slug": "files", "order": 8,
     "description": "National University document processing, submitted and tracked for you."},
    {"title": "Affiliated College Service", "color_hex": "#2352CC", "icon_slug": "building-community", "order": 9,
     "description": "Errands and paperwork at NU-affiliated colleges on your behalf."},
    {"title": "Bank Draft/Application", "color_hex": "#2352CC", "icon_slug": "building-bank", "order": 10,
     "description": "Bank draft preparation and account/application submission support."},
    {"title": "Medicine Courier/Collection", "color_hex": "#2352CC", "icon_slug": "pill", "order": 11,
     "description": "Medicine collection from pharmacy and courier delivery to you."},
    {"title": "Private University Student", "color_hex": "#2352CC", "icon_slug": "backpack", "order": 12,
     "description": "Campus errands and document support for private university students."},
    {"title": "Free Consulting/Info Support", "color_hex": "#2352CC", "icon_slug": "headset", "order": 13,
     "description": "Free guidance and information support for any of our services."},
    {"title": "Certificate/Mark", "color_hex": "#2352CC", "icon_slug": "certificate", "order": 14,
     "description": "Certificate and mark-sheet collection or submission on your behalf."},
    {"title": "Register Building", "color_hex": "#2352CC", "icon_slug": "building-estate", "order": 15,
     "description": "Sub-registrar office visits for land and deed registration work."},
    {"title": "NU/District rep.", "color_hex": "#2352CC", "icon_slug": "map-2", "order": 16,
     "description": "A local representative covering National University and district offices."},
    {"title": "Info Collectig", "color_hex": "#2352CC", "icon_slug": "clipboard-data", "order": 17,
     "description": "On-ground information gathering from offices or institutions you specify."},
    {"title": "Doc Correction", "color_hex": "#2352CC", "icon_slug": "file-pencil", "order": 18,
     "description": "Correction of errors on existing certificates and official documents."},
    {"title": "Affidavit", "color_hex": "#2352CC", "icon_slug": "file-check", "order": 19,
     "description": "Affidavit drafting and notarization handled at the court premises."},
    {"title": "Medicine Courier", "color_hex": "#2352CC", "icon_slug": "truck", "order": 20,
     "description": "Doorstep medicine delivery sourced from your preferred pharmacy."},
    {"title": "Study Mat. courier/DHL,Fedex", "color_hex": "#2352CC", "icon_slug": "package", "order": 21,
     "description": "Study materials shipped via DHL, FedEx, or other couriers."},
    {"title": "Department Office", "color_hex": "#2352CC", "icon_slug": "building-skyscraper", "order": 22,
     "description": "Academic department office visits for forms, signatures, and approvals."},
    {"title": "WES bank Pay", "color_hex": "#2352CC", "icon_slug": "credit-card", "order": 23,
     "description": "WES evaluation fee payment handled through the bank for you."},
    {"title": "Attestation DU", "color_hex": "#2352CC", "icon_slug": "file-certificate", "order": 24,
     "description": "Document attestation at Dhaka University, submitted and collected for you."},
    {"title": "Ministry Attestation", "color_hex": "#2352CC", "icon_slug": "building-monument", "order": 25,
     "description": "Ministry-level attestation of certificates for use abroad or locally."},
    {"title": "Drop Shipping", "color_hex": "#2352CC", "icon_slug": "box", "order": 26,
     "description": "Drop-shipping support for orders routed straight to your customer."},
    {"title": "Doc/Parcel Delivery", "color_hex": "#2352CC", "icon_slug": "truck-delivery", "order": 27,
     "description": "Document and parcel delivery across the city, tracked door to door."},
    {"title": "Medical Rep.", "color_hex": "#2352CC", "icon_slug": "stethoscope", "order": 28,
     "description": "A representative for hospital, clinic, or diagnostic center visits."},
    {"title": "Application & Payment", "color_hex": "#2352CC", "icon_slug": "file-invoice", "order": 29,
     "description": "Form submission and fee payment handled together, in one visit."},
    {"title": "Representative", "color_hex": "#2352CC", "icon_slug": "user", "order": 30,
     "description": "A general-purpose representative for errands you need done in person."},
    {"title": "In Campus", "color_hex": "#2352CC", "icon_slug": "school", "order": 31,
     "description": "On-campus errands for students who can't visit in person."},
    {"title": "Coordinator", "color_hex": "#2352CC", "icon_slug": "users", "order": 32,
     "description": "A coordinator to manage multi-step tasks across several offices."},
    {"title": "Purchasing", "color_hex": "#2352CC", "icon_slug": "shopping-bag", "order": 33,
     "description": "General purchasing of goods, delivered to your doorstep."},
    {"title": "Migration Certificate", "color_hex": "#2352CC", "icon_slug": "world", "order": 34,
     "description": "Migration certificate application and collection for university transfers."},
    {"title": "MOI & Testimonial", "color_hex": "#2352CC", "icon_slug": "certificate-2", "order": 35,
     "description": "Migration-of-Institution and testimonial certificates, processed on your behalf."},
    {"title": "Transcript Section", "color_hex": "#2352CC", "icon_slug": "file-description", "order": 36,
     "description": "Academic transcript requests submitted and collected from the section office."},
    {"title": "Partly Assist.", "color_hex": "#2352CC", "icon_slug": "help", "order": 37,
     "description": "Partial assistance for tasks you've already started but need help finishing."},
    {"title": "7 college", "color_hex": "#2352CC", "icon_slug": "school", "order": 38,
     "description": "Errands at any of the Dhaka University-affiliated seven colleges."},
    {"title": "Out of Dhaka city", "color_hex": "#2352CC", "icon_slug": "map-pin", "order": 39,
     "description": "Representative coverage for errands outside Dhaka city."},
    {"title": "BUET/Medical", "color_hex": "#2352CC", "icon_slug": "building-hospital", "order": 40,
     "description": "Errands at BUET or medical college/hospital campuses."},
]


class Command(BaseCommand):
    help = "Seeds (or updates) the Service catalog. Safe to re-run — upserts by title."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0
        for entry in SERVICES:
            _, created = Service.objects.update_or_create(
                title=entry["title"],
                defaults={
                    "color_hex": entry["color_hex"],
                    "icon_slug": entry["icon_slug"],
                    "order": entry["order"],
                    "description": entry["description"],
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(SERVICES)} services ({created_count} created, {updated_count} updated)."
        ))
