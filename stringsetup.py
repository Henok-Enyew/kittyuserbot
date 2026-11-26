#!/usr/bin/env python3
# (c) https://t.me/TelethonChat/37677
# This Source Code Form is subject to the terms of the GNU
# General Public License, v.3.0. If a copy of the GPL was not distributed with this
# file, You can obtain one at https://www.gnu.org/licenses/gpl-3.0.en.html.
"""Generate a Telethon STRING_SESSION for the userbot.

Run it locally (never on a shared server):

    python3 stringsetup.py

APP_ID / API_HASH are read from the environment if set, otherwise you are
asked for them. Get them from https://my.telegram.org -> API Development Tools.

The session string is printed and also sent to your Saved Messages.
Anyone who has it can use your account, so keep it secret.
"""

from __future__ import annotations

import asyncio
import os
from getpass import getpass

from telethon import TelegramClient, functions
from telethon.errors import (
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession

MAX_ATTEMPTS = 3


async def generate_string_session(
    api_id: int,
    api_hash: str,
    phone: str | None = None,
    *,
    method: str = "qr",
    send_to_saved: bool = True,
) -> str:
    """Log in interactively and return a Telethon StringSession string.

    ``method="qr"`` (default) shows a QR code to scan from the Telegram app on
    your phone, so no login code is needed. ``method="code"`` logs in with
    the phone number and the login code Telegram sends. Both ask for the
    two-step verification password if it is enabled. When ``send_to_saved``
    is true the string is also sent to the account's Saved Messages.
    """
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    try:
        if method == "qr":
            await _login_with_qr(client)
        else:
            await _login_with_code(client, phone)

        session_string = client.session.save()
        me = await client.get_me()

        if send_to_saved:
            await client.send_message(
                "me",
                "**KittyUserbot STRING_SESSION**\n\n"
                f"`{session_string}`\n\n"
                "⚠️ Do not share this with anyone. It gives full access to your account.",
            )

        name = me.first_name or ""
        print(f"\nLogged in as {name} (id {me.id}).")
        return session_string
    finally:
        await client.disconnect()


QR_ROUNDS = 6  # each QR is valid for ~30s, so this gives about 3 minutes


async def _login_with_qr(client: TelegramClient) -> None:
    qr = await client.qr_login()
    print(
        "\nOn your phone open Telegram > Settings > Devices > Link Desktop Device\n"
        "and scan the QR code below. A new one appears if it expires.\n"
    )
    for _ in range(QR_ROUNDS):
        _print_qr(qr.url)
        try:
            await qr.wait()
            return
        except asyncio.TimeoutError:
            print("QR code expired, here is a new one.\n")
            await qr.recreate()
        except SessionPasswordNeededError:
            await _sign_in_with_password(client)
            return
    raise SystemExit("No QR scan in time. Run the script again.")


def _print_qr(url: str) -> None:
    try:
        import qrcode
    except ImportError:
        print(
            "Install the 'qrcode' package (pip install qrcode) to see the QR here.\n"
            f"Or make a QR code of this link and scan it:\n{url}\n"
        )
        return
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    # invert=True draws dark modules as light blocks, which scans on dark terminals.
    qr.print_ascii(invert=True)


async def _login_with_code(client: TelegramClient, phone: str | None) -> None:
    if not phone:
        phone = input("Phone number with country code (e.g. +2519...): ").strip()

    try:
        sent = await client.send_code_request(phone)
    except PhoneNumberInvalidError:
        raise SystemExit("That phone number is invalid. Use the +<country><number> format.")

    _explain_delivery(sent)
    attempt = 0
    while attempt < MAX_ATTEMPTS:
        code = input(
            "Login code (or type 'resend' to get it another way): "
        ).replace(" ", "").strip()
        if code.lower() == "resend":
            try:
                sent = await client(
                    functions.auth.ResendCodeRequest(
                        phone_number=phone, phone_code_hash=sent.phone_code_hash
                    )
                )
                _explain_delivery(sent)
            except Exception as e:  # e.g. SendCodeUnavailableError, FloodWaitError
                print(f"Telegram refused to resend the code: {e}")
            continue
        if not code:
            continue
        attempt += 1
        try:
            await client.sign_in(phone, code, phone_code_hash=sent.phone_code_hash)
            return
        except PhoneCodeInvalidError:
            print(f"Wrong code ({attempt}/{MAX_ATTEMPTS}).")
        except PhoneCodeExpiredError:
            print("Code expired, sending a new one...")
            sent = await client.send_code_request(phone)
            _explain_delivery(sent)
        except SessionPasswordNeededError:
            await _sign_in_with_password(client)
            return
    raise SystemExit("Too many wrong codes. Run the script again.")


_DELIVERY = {
    "SentCodeTypeApp": (
        "in the Telegram app. Open Telegram on a phone/PC where you're already "
        "logged in and look for a message from the official 'Telegram' chat"
    ),
    "SentCodeTypeSms": "by SMS",
    "SentCodeTypeSmsWord": "by SMS (the code is a word)",
    "SentCodeTypeSmsPhrase": "by SMS (the code is a phrase)",
    "SentCodeTypeCall": "by a phone call that reads the code out",
    "SentCodeTypeFlashCall": "by a flash call (the code is the caller's number)",
    "SentCodeTypeMissedCall": "by a missed call; the code is the last digits of the caller's number",
    "SentCodeTypeEmailCode": "to your login email",
    "SentCodeTypeFragmentSms": "via fragment.com (anonymous number)",
    "SentCodeTypeFirebaseSms": (
        "by SMS through the official app's Firebase check, which third-party "
        "clients can't do. Type 'resend' to try another method"
    ),
    "SentCodeTypeSetUpEmailRequired": (
        "nowhere yet: Telegram wants you to set a login email first. Log in "
        "once in the official Telegram app, add a login email in "
        "Settings > Privacy and Security, then run this again"
    ),
}


_NEXT = {
    "CodeTypeSms": "by SMS",
    "CodeTypeCall": "by phone call",
    "CodeTypeFlashCall": "by flash call",
    "CodeTypeMissedCall": "by missed call",
    "CodeTypeFragmentSms": "via fragment.com",
}


def _explain_delivery(sent) -> None:
    """Tell the user where Telegram sent the code and what comes next."""
    kind = type(sent.type).__name__
    where = _DELIVERY.get(kind, f"via {kind}")
    print(f"\nTelegram sent the code {where}.")
    if getattr(sent.type, "email_pattern", None):
        print(f"Email: {sent.type.email_pattern}")
    if sent.next_type is not None:
        nxt = _NEXT.get(type(sent.next_type).__name__, "another way")
        wait = f" after {sent.timeout}s" if sent.timeout else ""
        print(f"If it doesn't arrive, type 'resend'{wait} to get it {nxt}.")
    else:
        print("Telegram offers no other delivery method for this number.")
    print()


async def _sign_in_with_password(client: TelegramClient) -> None:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        password = getpass("Two-step verification password: ")
        try:
            await client.sign_in(password=password)
            return
        except PasswordHashInvalidError:
            print(f"Wrong password ({attempt}/{MAX_ATTEMPTS}).")
    raise SystemExit("Too many wrong passwords. Run the script again.")


def _ask_credentials() -> tuple[int, str]:
    api_id = os.environ.get("APP_ID") or os.environ.get("API_ID")
    api_hash = os.environ.get("API_HASH")
    if not (api_id and api_hash):
        print(
            "Go to https://my.telegram.org, log in, open 'API Development Tools'\n"
            "and create an application to get your APP ID and API HASH.\n"
        )
    while True:
        api_id = api_id or input("APP ID: ").strip()
        if api_id.isdigit():
            break
        print("APP ID must be a number.")
        api_id = None
    api_hash = api_hash or input("API HASH: ").strip()
    return int(api_id), api_hash


def main() -> None:
    api_id, api_hash = _ask_credentials()
    choice = input(
        "\nHow do you want to log in?\n"
        "  1) Scan a QR code with the Telegram app on your phone (recommended)\n"
        "  2) Phone number + login code\n"
        "Choose 1 or 2 [1]: "
    ).strip()
    method = "code" if choice == "2" else "qr"
    session_string = asyncio.run(generate_string_session(api_id, api_hash, method=method))
    print("\nYour STRING_SESSION (also sent to your Saved Messages):\n")
    print(session_string)
    print("\nPut it in the STRING_SESSION config var. Keep it secret.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
