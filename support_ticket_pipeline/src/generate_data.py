"""
generate_data.py

Creates a synthetic, intentionally-messy support ticket dataset so the
pipeline has real data-quality problems to catch in the validation stage.

Bodies are generated the way a real helpdesk (Zendesk/Freshdesk/Intercom
style rich-text editor) actually stores them: as HTML, not plain text —
paragraphs, bold emphasis, links, HTML entities, quoted reply chains,
email signatures, and occasional malformed/junk markup. The cleaning
stage (clean_transform.py) is responsible for turning this back into
plain text before embedding.

Run:
    python src/generate_data.py
Output:
    data/raw/tickets_raw.csv
"""

import csv
import random
from pathlib import Path

random.seed(42)

# Each entry pairs a customer question with the resolution an agent actually
# gave for it, so the two stay thematically linked (see render_pair()) —
# this is what lets the chatbot answer with a real past resolution instead
# of just surfacing a similar-sounding question.
CATEGORIES = {
    "billing": [
        ("I was charged twice for my {plan} subscription this month, can you refund one?",
         "We've refunded the duplicate charge on your {plan} subscription — it should "
         "show back on your card within 5-7 business days."),
        ("My invoice shows a charge for {plan} but I cancelled last week.",
         "Your {plan} cancellation had already gone through, but the invoice was "
         "generated just before it processed. We've voided that charge and confirmed "
         "the subscription is cancelled."),
        ("Why is my card being charged {amount} when my plan is only {amount2}?",
         "The extra amount was a one-time prorated charge from your mid-cycle plan "
         "change. We've emailed an itemized receipt, and future invoices will show "
         "{amount2} as expected."),
        ("I need a copy of my invoice from last month for {plan}.",
         "We've emailed a PDF copy of last month's {plan} invoice to the address on "
         "file."),
        ("The discount code I used didn't apply to my {plan} order.",
         "That code had expired before checkout. We've manually applied the discount "
         "to your {plan} order and refunded the difference."),
    ],
    "login": [
        ("I can't log in, it keeps saying my password is incorrect even after reset.",
         "We've manually reset your password and sent a new reset link — the old "
         "link had expired, which is why the reset wasn't taking effect."),
        ("Two factor authentication code never arrives on my phone.",
         "Your account's SMS provider was flagging our messages as spam. We've "
         "switched your account to authenticator-app based 2FA, which doesn't rely "
         "on SMS."),
        ("My account got locked after too many login attempts, please unlock it.",
         "Your account is unlocked now. It locks automatically after 5 failed "
         "attempts within 10 minutes as a security measure."),
        ("I'm stuck on the login page, it just spins and never loads.",
         "This was a caching issue on our end after a recent deploy. It's fixed — "
         "please do a hard refresh (Ctrl/Cmd+Shift+R) and it should load normally."),
        ("Forgot password email never shows up in my inbox.",
         "Those emails were landing in spam for your provider. We've resent it and "
         "added a note to whitelist our support domain going forward."),
    ],
    "refund": [
        ("I want a refund for {plan}, it doesn't do what I need.",
         "We've processed a full refund for your {plan} plan — you should see it "
         "back on your original payment method within 5-7 business days."),
        ("Please process a refund, I cancelled within the trial period.",
         "Confirmed you cancelled inside the trial window, so this is a full refund. "
         "It's been processed and should post within a few business days."),
        ("Refund request: order was never delivered.",
         "Since the order never arrived, we've issued a full refund rather than a "
         "replacement, per your preference."),
        ("How long does a refund for {plan} usually take to show up?",
         "Refunds for {plan} typically post back to your card within 5-7 business "
         "days, depending on your bank."),
        ("I was told I'd get a refund two weeks ago and still nothing.",
         "We found the refund was stuck in a failed retry on our payment "
         "processor's side. It's been resubmitted and should post within 3 "
         "business days — sorry for the delay."),
    ],
    "bug": [
        ("The dashboard crashes every time I click on the {plan} report.",
         "This was a null-pointer bug triggered specifically by {plan}-tier report "
         "data. We've shipped a fix — please refresh and try again."),
        ("Export to CSV is broken, the file downloads empty.",
         "A recent change broke CSV export for accounts with more than 10k rows. "
         "That's fixed now; exports should include all rows again."),
        ("Getting a 500 error when I try to upload a file larger than 10MB.",
         "We've raised the upload size limit to 50MB and fixed the error handling "
         "so it fails gracefully with a clear message if a file is still too large."),
        ("The search bar returns no results even for terms I know exist.",
         "Our search index had fallen out of sync. We've rebuilt it and confirmed "
         "your query now returns the expected results."),
        ("Notifications stopped working after the last update.",
         "The last release accidentally disabled notification delivery for some "
         "accounts. We've re-enabled it for yours — you should start receiving "
         "them again."),
    ],
    "feature_request": [
        ("Could you add dark mode to the {plan} dashboard?",
         "Thanks for the suggestion — dark mode isn't available yet, but it's on "
         "our roadmap and we've logged your account as interested."),
        ("It would help a lot if we could export reports to Excel, not just CSV.",
         "Noted — Excel export isn't supported today, but we've filed this with "
         "product as a frequently requested export format."),
        ("Please add a bulk-delete option for old tickets.",
         "We don't have bulk-delete yet, but it's been added to the backlog based "
         "on requests like yours."),
        ("Any plan to support single sign-on for {plan} accounts?",
         "SSO for {plan} accounts is on our roadmap for a future release; we've "
         "added you to the notification list for when it ships."),
        ("Would love a mobile app version of this tool.",
         "A mobile app isn't in development yet, but we've logged the interest — "
         "the web dashboard is mobile-responsive in the meantime."),
    ],
    "shipping": [
        ("My order for {plan} hardware hasn't arrived, tracking hasn't updated in 5 days.",
         "The carrier lost tracking updates in transit; we've confirmed the package "
         "is moving again and it's now scheduled to arrive within 2 days."),
        ("Package arrived damaged, need a replacement.",
         "Sorry about that — we've shipped a free replacement with expedited "
         "shipping, no need to return the damaged item."),
        ("Wrong item was shipped, I ordered the {plan} kit not the basic one.",
         "We've shipped the correct {plan} kit with a prepaid return label for the "
         "wrong item — no charge for the mix-up."),
        ("Can I change my shipping address after the order was placed?",
         "Your order hadn't shipped yet, so we've updated the address on file — the "
         "confirmation email now reflects the new address."),
        ("Shipping cost seems way higher than quoted at checkout.",
         "That was a checkout bug applying international rates to a domestic "
         "order. We've refunded the difference in shipping cost."),
    ],
}

PLANS = ["Starter", "Pro", "Enterprise", "Team", "Basic"]
AMOUNTS = ["$29", "$49", "$99", "$199", "$9"]
CUSTOMER_NAMES = [
    "Alex Chen", "Priya Patel", "Jordan Smith", "Maria Garcia", "Sam Lee",
    "Taylor Brooks", "Nina Fischer", "Omar Haddad", "Grace Kim", "Liam O'Connor",
]

# A few noisy/typo variants so the cleaning stage has real work to do
NOISE_SUFFIXES = ["", "  ", "\n\nSent from my iPhone", "   thanks", "!!!", "???"]

SIGNATURES = [
    "<br><br>Best regards,<br>{name}",
    "<br><br>Thanks,<br>{name}<br>Sent from my iPhone",
    "<br>--<br>{name}<br>Account Manager, Acme Corp<br><a href=\"mailto:{email}\">{email}</a>",
    "<br><br>Sent from Yahoo Mail on Android",
    "<br><br>Cheers,<br>{name}",
]

QUOTE_TEMPLATE = (
    '<blockquote class="gmail_quote">On {date}, {name} wrote:<br>{prior_text}</blockquote>'
)


def messy(text: str) -> str:
    """Randomly inject whitespace/casing/typo noise into a subset of tickets."""
    if random.random() < 0.25:
        text = text.upper()
    if random.random() < 0.3:
        text = text.replace("please", "pls").replace("Please", "Pls")
    text = text + random.choice(NOISE_SUFFIXES)
    return text


def render_plain_body(category: str) -> str:
    """Question text only — used for the quoted-reply noise in htmlify()."""
    return render_pair(category)[0]


def render_pair(category: str) -> tuple[str, str]:
    """A (question, response) pair, formatted with the same plan/amount so the
    resolution stays consistent with what the customer actually asked about."""
    question_template, response_template = random.choice(CATEGORIES[category])
    fmt = {
        "plan": random.choice(PLANS),
        "amount": random.choice(AMOUNTS),
        "amount2": random.choice(AMOUNTS),
    }
    return question_template.format(**fmt), response_template.format(**fmt)


def htmlify(body: str, category: str, name: str, email: str) -> str:
    """Wrap a plain-text body the way a rich-text ticket form would submit it.

    Real helpdesk widgets (Zendesk, Freshdesk, Intercom, Front, ...) submit
    ticket bodies as HTML from a WYSIWYG editor, not plain text — even a
    one-line message comes back wrapped in <p> tags. This layers on the
    formatting, entities, links, signatures, quoted reply chains, and
    occasional malformed markup a real inbox would contain.
    """
    html = f"<p>{body}</p>"

    # Bold emphasis on a word/phrase
    if random.random() < 0.3:
        words = html.split(" ")
        if len(words) > 5:
            idx = random.randrange(2, len(words) - 1)
            words[idx] = f"<strong>{words[idx]}</strong>"
            html = " ".join(words)

    # HTML entities instead of raw characters (typical of copy-pasted rich text)
    html = html.replace("'", "&#39;").replace(" - ", " &ndash; ")
    if random.random() < 0.2:
        html = html.replace(" ", "&nbsp;", 1)

    # Feature requests sometimes come in as a bullet list
    if category == "feature_request" and random.random() < 0.3:
        html += (
            "<ul><li>would save us a lot of time</li>"
            "<li>several teammates asked for this too</li></ul>"
        )

    # Inline link (e.g. to a screenshot or reference ticket)
    if random.random() < 0.2:
        html += (
            f' <a href="https://help.acme.com/tickets/{random.randint(1000, 9999)}">'
            f"more details here</a>"
        )

    # Email signature block
    if random.random() < 0.5:
        sig = random.choice(SIGNATURES).format(name=name, email=email)
        html += sig

    # Quoted prior message in the thread (very common, pure noise for search)
    if random.random() < 0.15:
        prior_category = random.choice(list(CATEGORIES))
        prior_text = render_plain_body(prior_category)
        html += QUOTE_TEMPLATE.format(
            date=f"2026-0{random.randint(1, 8)}-{random.randint(1, 28):02d}",
            name=random.choice(CUSTOMER_NAMES),
            prior_text=prior_text,
        )

    # Junk markup copy-pasted from a webmail client (rare, but it happens)
    if random.random() < 0.05:
        html = '<style>.x{color:red}</style>' + html

    # Malformed HTML: a dropped closing tag (real inboxes are not well-formed)
    if random.random() < 0.1:
        html = html.replace("</p>", "", 1)

    return html


def make_ticket(ticket_id, category):
    body, response = render_pair(category)
    body = messy(body)
    subject = body.split(".")[0][:60].strip() or "Support request"
    name = random.choice(CUSTOMER_NAMES)
    email = f"user{ticket_id}@example.com"
    html_body = htmlify(body, category, name, email)
    return {
        "ticket_id": ticket_id,
        "subject": subject,
        "body": html_body,
        "category": category,
        "created_at": f"2026-0{random.randint(1,8)}-{random.randint(1,28):02d}",
        "customer_email": email,
        # The agent's resolution — plain text, not run through htmlify(), since
        # it's an internal note rather than customer-submitted rich text. This
        # is what the chatbot's RAG context uses to actually answer questions,
        # not just surface a similar past question.
        "response": response,
    }


def main():
    rows = []
    ticket_id = 1000
    for category in CATEGORIES:
        for _ in range(45):  # ~45 * 6 categories = 270 tickets
            rows.append(make_ticket(ticket_id, category))
            ticket_id += 1

    # --- Inject data-quality problems on purpose, for the validation exercise ---
    # 1) Missing body
    rows.append({"ticket_id": ticket_id, "subject": "Help", "body": "",
                 "category": "billing", "created_at": "2026-05-01",
                 "customer_email": "broken1@example.com"})
    ticket_id += 1
    # 2) Missing ticket_id
    rows.append({"ticket_id": "", "subject": "No id ticket", "body": "<p>This ticket has no id.</p>",
                 "category": "bug", "created_at": "2026-05-02",
                 "customer_email": "broken2@example.com"})
    # 3) Duplicate ticket_id (reuse an existing one)
    dup = dict(rows[5])
    rows.append(dup)
    # 4) PII in the body (should be caught/redacted by validation) — including
    #    PII embedded inside HTML markup (a signature mailto: link), which is
    #    exactly the kind of thing regex-based PII scrubbing must still catch.
    rows.append({"ticket_id": ticket_id, "subject": "Card issue",
                 "body": ("<p>My card 4111 1111 1111 1111 was charged twice, "
                          "call me at 555-123-4567.</p>"
                          "<br>--<br>Jamie Rivera<br>"
                          "<a href=\"mailto:jamie.rivera@personalmail.com\">"
                          "jamie.rivera@personalmail.com</a>"),
                 "category": "billing", "created_at": "2026-05-03",
                 "customer_email": "realcard@example.com"})
    ticket_id += 1
    # 5) Garbled / near-empty body
    rows.append({"ticket_id": ticket_id, "subject": "...", "body": "<p>asdkjh   </p>",
                 "category": "bug", "created_at": "2026-05-04",
                 "customer_email": "garbled@example.com"})
    ticket_id += 1
    # 6) A long, rambling ticket — every other ticket here is well under
    #    clean_transform.py's 400-char chunk threshold, so without this one
    #    the chunking logic would never actually split anything.
    rows.append({
        "ticket_id": ticket_id, "subject": "Ongoing billing issues across multiple cycles",
        "body": ("<p>I've been having an ongoing problem with your billing system for "
                 "the past three months and I need someone to actually look into this "
                 "properly instead of giving me a generic response. It started in March "
                 "when I upgraded from the Starter plan to the Pro plan, and since then "
                 "I've been charged the wrong amount every single cycle. The first month "
                 "I was charged for both plans on the same day, which support told me was "
                 "a proration error and promised to fix. The second month the charge was "
                 "correct but then three days later there was a second, unexplained "
                 "charge for a smaller amount that nobody has been able to explain to me. "
                 "This month, the fourth month in a row with a billing issue, I was "
                 "charged the full Enterprise rate even though I am still on the Pro plan "
                 "according to my account settings. I have screenshots of all of this if "
                 "it helps. At this point I've spent hours on chat with different agents "
                 "who each ask me to explain the whole history again from scratch, and I "
                 "would really appreciate it if whoever picks this up could actually read "
                 "through the account history instead of starting over. I just want my "
                 "billing to be correct and predictable going forward, and ideally some "
                 "kind of compensation for the time this has taken.</p>"),
        "category": "billing", "created_at": "2026-05-05",
        "customer_email": "longticket@example.com",
        "response": ("We reviewed your full billing history and found a proration bug "
                     "specific to Starter-to-Pro upgrades that also caused the incorrect "
                     "Enterprise-rate charge this cycle. All three erroneous charges have "
                     "been refunded in full, the underlying proration bug is fixed, and "
                     "we've credited one additional month of Pro service for the time "
                     "this took to resolve."),
    })

    random.shuffle(rows)

    out_path = Path(__file__).resolve().parents[1] / "data" / "raw" / "tickets_raw.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ticket_id", "subject", "body", "category",
                                                "created_at", "customer_email", "response"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} tickets to {out_path}")


if __name__ == "__main__":
    main()
