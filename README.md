# TALEED | Saudi Cities, Culture & Heritage

[![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![UI](https://img.shields.io/badge/Design-Editorial%20Heritage-a65f38)](https://github.com/)

**TALEED (تَليد)** is an immersive, editorial Saudi cultural and heritage web platform built with Django. Designed to celebrate the Kingdom of Saudi Arabia's authentic legacy, TALEED takes visitors on an interactive journey across Saudi administrative regions, capitals, and governorates. Through high-fidelity photography, historical narratives, traditional architecture, artisanal crafts, local gastronomy, and traditional attire, TALEED captures the living identity of Saudi cities.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Technologies Used](#technologies-used)
- [Core Features & Pages](#core-features--pages)
- [Project Architecture & Directory Structure](#project-architecture--directory-structure)
- [Template Inheritance & Component Design](#template-inheritance--component-design)
- [Dynamic Routing & Request Handling](#dynamic-routing--request-handling)
- [Static Asset Pipeline & Revisioning](#static-asset-pipeline--revisioning)
- [Theme & Internationalization (RTL/LTR)](#theme--internationalization-rtlltr)
- [Responsive Design & Device Support](#responsive-design--device-support)
- [Installation & Setup Guide](#installation--setup-guide)
- [Automated Testing](#automated-testing)
- [Satisfaction of UNIT-PROJECT-2 Requirements](#satisfaction-of-unit-project-2-requirements)
- [Media, Imagery & Attribution](#media-imagery--attribution)
- [Academic Project Acknowledgment](#academic-project-acknowledgment)

---

## Project Overview

*Taleed* (meaning ancient, deeply rooted heritage in Arabic) bridges deep historical documentation with modern editorial web design. Rather than relying on generic tourism brochures, the platform organizes Saudi heritage geographically and culturally:

1. **Geographic Atlas**: Explores all 13 administrative provincial capitals plus 35 curated governorates (spanning historical architecture, geographic profiles, local attire, famous produce, and landmark records).
2. **Cultural Thematic Pathways**: Explores cross-regional heritage across three core pillars:
   - **Architecture (عمارة تحكي)**: Rowshan wooden latticework, mud-brick towers, coral masonry, and traditional desert building craft.
   - **Artisanal Crafts (حِرف تُورَّث)**: Al-Sadu weaving, palm frond weaving (*Khous*), pottery, and regional artistry.
   - **Gastronomy & Culinary Arts (مذاق يبقى)**: Traditional dishes, heritage recipes, dates, and regional agricultural crops.
3. **Bilingual & Multi-Themed**: Native Arabic layout (RTL) with full English localization (LTR) and seamless light/dark mode switching.

---

## Technologies Used

- **Backend Framework**: [Django 5.2](https://www.djangoproject.com/) (MVT architecture)
- **Programming Language**: Python 3.12+ (compatible up to Python 3.14)
- **Database**: SQLite 3 (ORM integration with `City` and `Governorate` relational models)
- **Frontend / Markup**: Semantic HTML5 with complete ARIA accessibility landmarks
- **Styling**: Vanilla Modern CSS (CSS Custom Properties, CSS Grid, Flexbox, Fluid Typography with `clamp()`)
- **Typography**: Web fonts licensed under SIL Open Font License (OFL):
  - *Amiri*: Classical Arabic serif headings
  - *Aref Ruqaa*: Calligraphic heritage typography and poetic verses
  - *Readex Pro*: Clean, legible modern UI and story body text
  - *Markazi Text*: Editorial body text
- **Client Scripting**: Vanilla JavaScript (ES6+) for theme toggling, interactive image fallbacks, asynchronous story bookmarks, and accessibility management (zero heavy frontend framework dependencies)
- **Internationalization (i18n)**: GNU `gettext` message catalogs (`django.po` / `django.mo`) for Arabic and English

---

## Core Features & Pages

The application delivers **58 distinct content destinations** powered by dynamic Django views and template inheritance:

| Page / Route | URL Pattern | Description |
|---|---|---|
| **Home (الرئيسية)** | `/` | Editorial landing page featuring hero panoramic illustrations, mission introduction, cultural vignettes, and pathways into architecture, crafts, and food. |
| **City Doors (اكتشف المدن)** | `/cities/` | Visual exhibition featuring an expansive opening hero card (Al Madinah), preview cards, regional filters (Western, Central, Southern, Northern, Eastern), and the remaining cities exhibition grid. |
| **Saved Stories (حكاياتي)** | `/cities/?saved=1` | Filtered doorway view displaying all cities and governorates bookmarked by the user in client cookies. |
| **City Atlas (تفاصيل المدينة)** | `/cities/<slug>/` | In-depth atlas for the 13 administrative capitals (e.g. `madinah`, `riyadh`, `makkah`, `abha`, `tabuk`, `hail`, `jazan`), covering historical landmarks, timeline, men's & women's attire, culinary heritage, and child governorates. |
| **Governorate Detail** | `/cities/<capital>/governorates/<slug>/` | Specialized profiles for 35 historical governorates (e.g., AlUla, Rijal Almaa, Farasan, Tayma, Shaqra, Onaizah, Al-Ahsa). |
| **Cultural Topic: Architecture** | `/culture/architecture/` | Curated showcase of traditional Saudi structural typologies and regional building materials. |
| **Cultural Topic: Crafts** | `/culture/crafts/` | Interactive catalog of living traditional handicrafts passed down through generations. |
| **Cultural Topic: Food** | `/culture/food/` | Paginated culinary exhibition of regional dishes and local agricultural produce with regional filtering. |
| **About TALEED (عن تليد)** | `/about/` | The editorial story, research standards, geographic scope, and preservation philosophy. |
| **Preferences & Theme API** | `/preferences/theme/` | POST endpoint persisting dark/light mode preference in secure client cookies. |
| **Language Toggle API** | `/preferences/language/` | Django i18n endpoint handling Arabic (ar) / English (en) switching with redirect. |

---

## Project Architecture & Directory Structure

```text
UNIT-PROJECT-2/
├── config/                     # Django project configuration
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py             # App settings, static paths, i18n, middleware
│   ├── urls.py                 # Root URLconf
│   └── wsgi.py
├── main/                       # Core Django application
│   ├── management/commands/    # Custom manage.py management commands
│   │   ├── compile_translations.py
│   │   ├── export_media.py
│   │   ├── prepare_images.py
│   │   ├── sync_geography.py   # Synchronizes JSON geography with SQLite models
│   │   └── upload_cdn.py       # Cloudinary CDN preparation and upload
│   ├── templatetags/           # Custom template tags and filters
│   │   └── site_assets.py      # Asset revisioning tag {% asset %} and {% localize %}
│   ├── models.py               # City & Governorate ORM models
│   ├── views.py                # View handlers (home, cities, atlas, culture, about)
│   ├── urls.py                 # App-level URL routing
│   ├── geography.py            # Geographic registry, plates, and slug resolution
│   ├── culture.py              # Thematic culture data loaders
│   ├── content.py              # Editorial catalog & media resolver
│   └── tests.py                # 68 automated unit and integration tests
├── data/                       # Structured editorial JSON repository
│   ├── cities.json             # City identities, titles, and historical narratives
│   ├── governorates.json       # Governorate metadata and relationships
│   ├── geography.json          # Regional hierarchy and display order
│   ├── place_profiles.json     # Detailed historical landmarks and timelines
│   ├── local_culture.json      # Regional culinary, fruits, and attire documentation
│   ├── culture.json            # Architecture, crafts, and food topic catalogs
│   └── media.json              # Image registry, captions, and attribution licenses
├── locale/                     # Translation files (Arabic / English)
│   └── en/LC_MESSAGES/
│       ├── django.po           # Editable English translation catalog
│       └── django.mo           # Compiled binary catalog
├── static/                     # Source static assets
│   ├── css/                    # Modular stylesheet architecture
│   │   ├── foundation.css      # CSS reset, design tokens, color palette, box-sizing
│   │   ├── reading.css         # Typography scale, Arabic serif/sans font definitions
│   │   ├── editorial-system.css# Unified editorial layout and spacing rules
│   │   ├── interface.css       # Header, navigation, dark-mode toggles, buttons
│   │   ├── home-hero.css       # Hero scene styling and decorative vectors
│   │   ├── pathways.css        # Cultural pathways cards
│   │   ├── city-doors.css      # Panoramic city exhibition and doorway grids
│   │   ├── atlas.css           # Landmark profiles, timelines, and city sheets
│   │   ├── place-culture.css   # Attire, dishes, and governorate cards
│   │   └── culture.css         # Topic galleries and pagination
│   ├── fonts/                  # OFL web fonts (Amiri, Aref Ruqaa, Readex Pro, Markazi)
│   ├── images/                 # Optimized WebP and JPG city and heritage imagery
│   └── js/
│       ├── main.js             # Theme toggle, navigation menu, cookie-based bookmarks
│       ├── media.js            # Image fallback handler
│       └── atlas.js            # Dynamic tab switching and media galleries
├── templates/                  # Django HTML templates
│   ├── base.html               # Master layout wrapper with header, footer, i18n, & theme
│   ├── 404.html                # Custom branded error page
│   ├── includes/               # Reusable template components (partials)
│   │   ├── city_door.html      # Individual city doorway card
│   │   ├── editorial_footer.html# Branded footer with links and colophon
│   │   ├── image.html          # Responsive picture element with WebP fallbacks
│   │   ├── photo_credit.html   # Media attribution and licensing badge
│   │   ├── place_culture.html  # Food, fruits, and attire tabbed layout
│   │   ├── place_plate.html    # Child governorate card
│   │   └── save.html           # Asynchronous bookmark button
│   └── main/                   # Page templates extending base.html
│       ├── home.html           # Landing page
│       ├── cities.html         # City discovery directory
│       ├── city_detail.html    # City & Governorate Atlas page
│       ├── culture_topic.html  # Architecture, Crafts, and Food pages
│       └── about.html          # About TALEED page
├── requirements.txt            # Python dependencies
├── manage.py                   # Django management executable
└── SETUP.md                    # Setup and operational instructions
```

---

## Template Inheritance & Component Design

The frontend follows strict DRY (Don't Repeat Yourself) Django template inheritance:

1. **`templates/base.html`**:
   - Manages HTML document metadata, viewport settings, preloading of critical Arabic fonts, and dynamic `lang` and `dir` attributes (`dir="rtl"` for Arabic, `dir="ltr"` for English).
   - Injects the persistent header (wordmark brand, accessible mobile navigation drawer, language switch form, bookmarked stories counter, and dark mode toggle).
   - Provides structured blocks (`{% block content %}`, `{% block layout_css %}`, `{% block extra_css %}`).
   - Renders the common `editorial_footer.html` partial and client toast notifications.

2. **Modular Includes (`templates/includes/`)**:
   - `city_door.html`: Standardized card used across `/cities/`, adapting cleanly between the expansive featured view and grid-based exhibition cards.
   - `image.html`: Encapsulates high-performance image rendering using `<picture>`, `srcset`, and `loading="lazy"`.
   - `place_culture.html`: Reusable cultural stage showing authentic clothing, cuisine, and produce across both capitals and governorates.

---

## Dynamic Routing & Request Handling

TALEED leverages clean, parameterized Django URLs configured in `main/urls.py`:

- **Slug-based Dynamic Resolution**:
  - `/cities/<slug:slug>/`: Matches capital cities directly from the database and JSON profile registry.
  - `/cities/<slug:capital_slug>/governorates/<slug:slug>/`: Hierarchically routes to specific governorates while maintaining parent capital breadcrumbs and context.
  - `/culture/<slug:topic>/`: Routes to `architecture`, `crafts`, or `food`.
- **Query Parameter Handling**:
  - `/cities/?region=west`: Filters cities by geographical sector (`west`, `central`, `south`, `north`, `east`).
  - `/cities/?saved=1`: Filters the directory to only display places saved in the user's cookies.
  - `/culture/food/?page=2`: Handles Django server-side pagination for traditional dishes.

---

## Static Asset Pipeline & Revisioning

- **Custom Cache-Busting (`site_assets.py`)**:
  To prevent browsers from caching stale CSS and JavaScript during development and updates, all static assets are loaded via a custom tag:
  ```django
  {% load site_assets %}
  <link rel="stylesheet" href="{% asset 'css/foundation.css' %}">
  ```
  The `{% asset %}` tag automatically appends the file's modification timestamp in nanoseconds (`?v=<timestamp>`).
- **CDN Integration**:
  Built-in support for Cloudinary CDN media delivery through `main/media_delivery.py`. If a CDN manifest is detected (`data/cdn_manifest.json`), images are served from high-speed edge servers; otherwise, the pipeline transparently falls back to local static files.

---

## Theme & Internationalization (RTL/LTR)

1. **Dark & Light Mode**:
   - The user's theme preference (`light` or `dark`) is stored in a `theme` cookie with `SameSite='Lax'` protection.
   - The HTML root receives `data-theme="light"` or `data-theme="dark"`.
   - The color palette is completely variable-driven in `foundation.css` and `editorial-system.css`, transitioning seamlessly from ivory and desert cream to nocturnal oasis charcoal.
2. **Full Bilingual Support**:
   - Default language: **Arabic (العربية)** with proper right-to-left layout (`dir="rtl"`).
   - English language: Supported via Django's native internationalization system (`rosetta`/`gettext`). Switching to English toggles `dir="ltr"` and renders curated English typography and translations.

---

## Responsive Design & Device Support

The layout has been engineered and tested across standard screen resolutions:

- **Mobile Viewports (320px – 430px)**: Compact single-column card grids, accessible touch navigation menu, and scaled typography.
- **Tablets & iPads (768px – 1024px)**: Balanced 2-column exhibition grids, adapted side-by-side previews, and touch-friendly interactive tabs.
- **Laptops & Desktops (1280px – 1440px)**: Panoramic doorway layout, 3-column exhibition grids, and expansive photographic spreads.
- **Ultrawide & Large Screens (1920px+)**: Content constrained to `max-width: 1840px` with fluid margins, preventing stretched lines or visual distortion.

---

## Installation & Setup Guide

### Prerequisites
- Python 3.12 or newer installed on your system.
- Git.

### 1. Clone the Repository
```bash
git clone <repository-url>
cd UNIT-PROJECT-2
```

### 2. Create and Activate a Virtual Environment
- **On Windows (PowerShell)**:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
- **On macOS / Linux**:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations
```bash
python manage.py migrate
```

### 5. Synchronize Geography and Data
Run the custom management command to populate the database with all 13 administrative capitals and 35 governorates from the structured JSON files:
```bash
python manage.py sync_geography
```

### 6. Compile Translation Messages
Compile the bilingual GNU gettext catalogs:
```bash
python manage.py compile_translations
```

### 7. Run the Development Server
```bash
python manage.py runserver
```
Visit **http://127.0.0.1:8000/** in your browser.

*(If port 8000 is occupied, you may specify another port such as `python manage.py runserver 127.0.0.1:8001`)*.

---

## Automated Testing

TALEED includes a comprehensive automated test suite in `main/tests.py` covering URL routing, view status codes, database integrity, bookmarking cookies, translation compilation, and responsive template tags.

To execute the test suite:
```bash
python manage.py test main
```
**Verification Result**:
```text
Ran 68 tests in ~33s
OK
System check identified no issues (0 silenced).
```

---

## Satisfaction of UNIT-PROJECT-2 Requirements

TALEED was built specifically to fulfill and exceed all criteria outlined for **UNIT-PROJECT-2**:

| Requirement | Implementation in TALEED |
|---|---|
| **Use Django** | Built on Django 5.2 using standard MVT architecture (`config` project, `main` application). |
| **Templates & Inheritance** | Base template (`base.html`) extended across `home.html`, `cities.html`, `city_detail.html`, `culture_topic.html`, `about.html`, and 404 handler, with reusable partials in `templates/includes/`. |
| **Dynamic URLs** | Slugs dynamically resolve capitals (`/cities/<slug>/`), governorates (`/cities/<capital>/governorates/<slug>/`), and topics (`/culture/<topic>/`). |
| **Static Files** | Organized modular CSS (`foundation.css`, `reading.css`, `city-doors.css`), custom fonts, WebP images, and client scripts. |
| **Homepage + at least 6 pages** | Features **58 unique content pages** (Homepage, About page, Directory, 3 Culture pages, 13 City Atlases, and 35 Governorate Atlases). |
| **Coherent, uniform design** | Bespoke Saudi heritage editorial design system with consistent color tokens, typography hierarchy, and visual motifs. |
| **Dark and Light Mode** | Cookie-persisted dark and light modes with instant toggling and high-contrast accessible color contrast ratios. |
| **Responsive Design** | Fully responsive across mobile (320px–430px), tablet (768px–1024px), laptop (1280px–1440px), and desktop (1920px+). |
| **CDN / Media Pipeline** | Built-in management command (`upload_cdn.py`) and media delivery pipeline supporting Cloudinary CDN integration for cloud media hosting. |

---

## Media, Imagery & Attribution

- **Cultural & Heritage Imagery**: Photographs of historical landmarks, regional attire, and cultural artifacts are curated from documented historical archives, open cultural registries, and Creative Commons / Wikimedia Commons sources with proper attribution credits embedded in `data/media.json`.
- **Photo Credits**: Reusable photo credit components (`includes/photo_credit.html`) render source attribution links directly on landmark photos and editorial figures.
- **Visual Artworks**: Heritage door collages, panoramic architectural illustrations, and pathway vignettes were designed specifically to represent the shared roots and architectural diversity of the Kingdom.

---

## Academic Project Acknowledgment

This project was developed as an academic submission for **UNIT-PROJECT-2**, demonstrating mastery of backend Django development, relational database modeling, dynamic URL dispatching, template inheritance, responsive UI design, and bilingual web application architecture.
