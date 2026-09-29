# Service icons

Outline SVG icons from [Tabler Icons](https://tabler.io/icons) (MIT licensed),
downloaded from `github.com/tabler/tabler-icons` (`icons/outline/`).

Each `Service.icon_slug` (see `tasks/models.py`) is the filename here minus
`.svg`. Icons use `stroke="currentColor"`, so the app tints them (usually
white) rather than baking in a fixed color — that's what lets one icon work
across every service's own `color_hex` background.

To add a new one: pick a slug from https://tabler.io/icons, download
`https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/<slug>.svg`
into this folder, then set that `Service`'s `icon_slug` in admin (or
`seed_services.py`) to match.
