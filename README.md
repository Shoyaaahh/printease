# PrintEase

A web-based printing service quotation, design preview, and order management system
for Marian's Printing Services — built with Flask + SQLite.

## Features

- **Accounts:** customer sign up / login, two customer types (Normal, Student — students
  enter a student ID in the format `XX-XXXXX`, e.g. `22-01234`). Optional phone number
  at signup for future SMS updates.
- **Separate admin login** with its own dashboard (seeded automatically on first run).
- **Six print services to choose from:**
  - Normal Print (on paper)
  - Tarpaulin
  - Shirt Printing
  - Soft Bind
  - Hard Bind
  - Laminate

  Each service shows only the fields relevant to it (paper size & pages for
  documents, width/height in feet for tarpaulins, size & color for shirts, etc.).
- **Automatic price estimation:** every request gets an estimated price the moment
  it's submitted, based on an editable price list in `pricing.py`. Urgent requests
  get a +20% rush surcharge automatically. This is an *estimate* — the shop
  confirms the final price when accepting the request.
- **Design/file preview:** image uploads (JPG/PNG) preview immediately. PDF uploads
  get an automatic first-page thumbnail if the optional `PyMuPDF` package is
  installed (see requirements.txt) — otherwise they just fall back to a
  download link, no errors.
- **Priority lane:** requests from students OR marked urgent are automatically
  surfaced first on the admin dashboard, separate from the regular queue.
- **Admin workflow:** review a request, accept it and set a completion date (or
  cancel it), then mark it completed. Each action notifies the customer.
- **Order history & search (admin):** filter past and current requests by
  customer name/email, status, service type, and date range.
- **Notifications:** always saved in-app (visible on the customer's dashboard).
  Email is sent too if you configure SMTP settings (see below) — if you don't,
  it's silently skipped and nothing breaks. SMS is stubbed out (see below).
- **Add-on notes:** customers can add a follow-up note/comment to a request after
  submitting it (e.g. "please also print 2 more copies").

## Project structure

```
printease/
├── app.py                     # App factory, admin auto-seed, entry point
├── config.py                  # App configuration (DB path, upload folder, mail, etc.)
├── extensions.py              # Shared db / login_manager / mail instances
├── models.py                  # User, PrintRequest, RequestComment, Notification
├── pricing.py                 # Service types, price list, price calculator
├── notifications.py           # In-app + email + SMS-stub notification helper
├── file_preview.py            # Generates a preview thumbnail for uploads
├── requirements.txt
├── auth/routes.py             # signup / login / logout
├── customer/routes.py         # dashboard, submit request, request detail
├── admin/routes.py            # dashboard, history/search, accept/complete/cancel
├── templates/                 # Jinja2 + Bootstrap 5 templates
└── static/
    ├── css/style.css
    └── uploads/                # uploaded design files + generated previews land here
```

## Setup (in VS Code / terminal)

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   (Optional) also install `PyMuPDF` for PDF thumbnail previews:
   ```bash
   pip install PyMuPDF
   ```
3. Run the app:
   ```bash
   python app.py
   ```
4. Open **http://127.0.0.1:5000** in your browser.

The database (`printease.db`, SQLite) and `static/uploads/` folder are created
automatically the first time you run the app.

### Default admin login
- Email: `admin@printease.com`
- Password: `admin123`

(Change or remove `_seed_admin()` in `app.py` once you set up real accounts.)

## Adjusting prices

Open `pricing.py` — everything is in one `PRICING` dict, plus `URGENT_SURCHARGE_RATE`
for the rush fee percentage. Change the numbers to match the shop's real price list;
nothing else in the app needs to change.

## Turning on real email notifications

By default, email is skipped (in-app notifications still work fine). To enable it,
set these environment variables before running the app (e.g. in a `.env` file or
your terminal):

```bash
export MAIL_SERVER=smtp.gmail.com
export MAIL_PORT=587
export MAIL_USE_TLS=true
export MAIL_USERNAME=your_email@gmail.com
export MAIL_PASSWORD=your_app_password   # use an App Password, not your real password
export MAIL_DEFAULT_SENDER=your_email@gmail.com
```

## Turning on real SMS notifications

SMS isn't wired to a live provider out of the box — that needs a paid SMS API
account and your own credentials. `notifications.py` includes a ready example for
**Semaphore** (a common SMS API for Philippine numbers: https://semaphore.co):

1. Sign up for an account and get an API key.
2. `export SEMAPHORE_API_KEY=your_key_here`
3. Uncomment the `requests.post(...)` block in `notifications.py`.

Until then, PrintEase just logs what *would* have been sent, so nothing breaks.

## Notes / things you may want to add next

- Editable business settings from an admin UI (paper sizes, prices) instead of
  editing `pricing.py` directly.
- Multiple files per request (e.g. a multi-page tarpaulin design plus a mockup).
- Rejection reason field when an admin cancels a request.
- Customer-facing order receipt/invoice PDF once a request is completed.
