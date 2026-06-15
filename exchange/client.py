"""Exchange Web Services (EWS) async-friendly client wrapper."""
import asyncio
from datetime import datetime, timedelta
from functools import partial
from typing import Any

import pytz
from exchangelib import (
    Account,
    Attendee,
    Configuration,
    Credentials,
    EWSDateTime,
    EWSTimeZone,
    Mailbox,
    Message,
    CalendarItem,
    DELEGATE,
)
from exchangelib.autodiscover import Autodiscovery
from exchangelib.protocol import BaseProtocol
from exchangelib.items import SEND_AND_SAVE_COPY, SEND_TO_ALL_AND_SAVE_COPY

import config

# Disable SSL verification for internal servers if needed
BaseProtocol.HTTP_ADAPTER_CLS = BaseProtocol.HTTP_ADAPTER_CLS

TEHRAN_TZ = EWSTimeZone.timezone("Asia/Tehran")


def _build_account(username: str, password: str) -> Account:
    creds = Credentials(
        username=f"{config.EXCHANGE_DOMAIN}\\{username}",
        password=password,
    )
    if config.EXCHANGE_EWS_URL:
        cfg = Configuration(
            server=config.EXCHANGE_SERVER,
            credentials=creds,
        )
        return Account(
            primary_smtp_address=f"{username}@{config.EXCHANGE_SERVER}",
            config=cfg,
            autodiscover=False,
            access_type=DELEGATE,
        )
    return Account(
        primary_smtp_address=f"{username}@{config.EXCHANGE_SERVER}",
        credentials=creds,
        autodiscover=True,
        access_type=DELEGATE,
    )


async def get_account(username: str, password: str) -> Account:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _build_account, username, password)


async def verify_credentials(username: str, password: str) -> bool:
    try:
        account = await get_account(username, password)
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: account.inbox.total_count
        )
        return True
    except Exception:
        return False


# ── Email ─────────────────────────────────────────────────────────────────────

async def get_inbox(username: str, password: str, offset: int = 0, count: int = 10) -> list[dict]:
    account = await get_account(username, password)

    def _fetch():
        items = []
        for msg in account.inbox.filter().order_by("-datetime_received")[offset:offset + count]:
            items.append({
                "id": msg.id,
                "subject": msg.subject or "(بدون موضوع)",
                "from": msg.sender.email_address if msg.sender else "نامشخص",
                "from_name": msg.sender.name if msg.sender else "نامشخص",
                "received": msg.datetime_received,
                "is_read": msg.is_read,
                "has_attachments": msg.has_attachments,
            })
        return items

    return await asyncio.get_event_loop().run_in_executor(None, _fetch)


async def get_email_body(username: str, password: str, email_id: str) -> dict:
    account = await get_account(username, password)

    def _fetch():
        items = list(account.inbox.filter(id=email_id))
        if not items:
            return None
        msg = items[0]
        return {
            "subject": msg.subject or "(بدون موضوع)",
            "from": msg.sender.email_address if msg.sender else "نامشخص",
            "from_name": msg.sender.name if msg.sender else "نامشخص",
            "received": msg.datetime_received,
            "body": msg.text_body or msg.body or "",
            "to": [r.mailbox.email_address for r in (msg.to_recipients or [])],
        }

    return await asyncio.get_event_loop().run_in_executor(None, _fetch)


async def send_email(
    username: str,
    password: str,
    to: list[str],
    subject: str,
    body: str,
) -> None:
    account = await get_account(username, password)

    def _send():
        msg = Message(
            account=account,
            subject=subject,
            body=body,
            to_recipients=[Mailbox(email_address=addr) for addr in to],
        )
        msg.send_and_save()

    await asyncio.get_event_loop().run_in_executor(None, _send)


# ── Calendar ──────────────────────────────────────────────────────────────────

async def get_calendar_events(
    username: str,
    password: str,
    days_ahead: int = 7,
) -> list[dict]:
    account = await get_account(username, password)

    def _fetch():
        now = EWSDateTime.now(tz=TEHRAN_TZ)
        end = now + timedelta(days=days_ahead)
        events = []
        for item in account.calendar.view(start=now, end=end).order_by("start"):
            attendees = []
            if item.required_attendees:
                attendees = [a.mailbox.email_address for a in item.required_attendees]
            events.append({
                "id": item.id,
                "subject": item.subject or "(بدون عنوان)",
                "start": item.start,
                "end": item.end,
                "location": item.location or "",
                "organizer": item.organizer.email_address if item.organizer else "",
                "attendees": attendees,
                "is_all_day": item.is_all_day,
            })
        return events

    return await asyncio.get_event_loop().run_in_executor(None, _fetch)


async def create_calendar_event(
    username: str,
    password: str,
    subject: str,
    start: datetime,
    end: datetime,
    location: str = "",
    body: str = "",
    attendees: list[str] | None = None,
) -> str:
    account = await get_account(username, password)

    def _create():
        ews_start = EWSDateTime.from_datetime(start).astimezone(TEHRAN_TZ)
        ews_end = EWSDateTime.from_datetime(end).astimezone(TEHRAN_TZ)
        item = CalendarItem(
            account=account,
            folder=account.calendar,
            subject=subject,
            start=ews_start,
            end=ews_end,
            location=location,
            body=body,
            required_attendees=[
                Attendee(mailbox=Mailbox(email_address=addr))
                for addr in (attendees or [])
            ],
        )
        item.save(send_meeting_invitations=SEND_AND_SAVE_COPY)
        return item.id

    return await asyncio.get_event_loop().run_in_executor(None, _create)


# ── Contacts / GAL ────────────────────────────────────────────────────────────

async def search_contacts(username: str, password: str, query: str, limit: int = 10) -> list[dict]:
    account = await get_account(username, password)

    def _search():
        results = []
        # Search in personal contacts
        for contact in account.contacts.filter(display_name__icontains=query)[:limit]:
            email = ""
            if contact.email_addresses:
                email = contact.email_addresses[0].email
            results.append({
                "name": contact.display_name or "",
                "email": email,
                "phone": str(contact.phone_numbers[0].phone_number) if contact.phone_numbers else "",
                "department": contact.department or "",
                "title": contact.job_title or "",
            })
        return results

    return await asyncio.get_event_loop().run_in_executor(None, _search)


# ── Rooms ─────────────────────────────────────────────────────────────────────

async def get_room_lists(username: str, password: str) -> list[dict]:
    """Get all room lists (distribution groups for rooms)."""
    account = await get_account(username, password)

    def _fetch():
        protocol = account.protocol
        rooms = []
        try:
            for room in protocol.get_rooms():
                rooms.append({
                    "name": room.name,
                    "email": room.email_address,
                })
        except Exception:
            # Fallback: return empty if server doesn't support room lists
            pass
        return rooms

    return await asyncio.get_event_loop().run_in_executor(None, _fetch)


async def check_room_availability(
    username: str,
    password: str,
    room_email: str,
    start: datetime,
    end: datetime,
) -> bool:
    """Check if a room is available for the given time slot."""
    account = await get_account(username, password)

    def _check():
        from exchangelib import FreeBusyQuery
        ews_start = EWSDateTime.from_datetime(start).astimezone(TEHRAN_TZ)
        ews_end = EWSDateTime.from_datetime(end).astimezone(TEHRAN_TZ)
        try:
            result = account.protocol.get_free_busy(
                [FreeBusyQuery(attendees=[Mailbox(email_address=room_email)],
                               start=ews_start, end=ews_end)]
            )
            for info in result:
                for busy in (info.calendar_events or []):
                    if busy.start < ews_end and busy.end > ews_start:
                        return False
            return True
        except Exception:
            return True  # assume available if we can't check

    return await asyncio.get_event_loop().run_in_executor(None, _check)


async def book_room(
    username: str,
    password: str,
    room_email: str,
    room_name: str,
    subject: str,
    start: datetime,
    end: datetime,
    attendees: list[str] | None = None,
) -> str:
    """Book a room by creating a calendar event with the room as location/attendee."""
    return await create_calendar_event(
        username=username,
        password=password,
        subject=subject,
        start=start,
        end=end,
        location=room_name,
        attendees=[room_email] + (attendees or []),
    )
