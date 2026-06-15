"""AI-powered room booking agent using Requesty (OpenAI-compatible) with tool use."""
import json
from datetime import datetime
from typing import Any

from openai import AsyncOpenAI
import pytz

import config
from exchange import client as exchange

TEHRAN_TZ = pytz.timezone("Asia/Tehran")

_client = AsyncOpenAI(
    api_key=config.REQUESTY_API_KEY,
    base_url=config.REQUESTY_BASE_URL,
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_available_rooms",
            "description": "لیست اتاق‌های جلسه موجود در سازمان را برمی‌گرداند.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_room_availability",
            "description": "بررسی می‌کند که آیا یک اتاق در بازه زمانی مشخص آزاد است.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_email": {"type": "string", "description": "آدرس ایمیل اتاق"},
                    "start_time": {"type": "string", "description": "زمان شروع ISO 8601"},
                    "end_time": {"type": "string", "description": "زمان پایان ISO 8601"},
                },
                "required": ["room_email", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_room",
            "description": "یک اتاق جلسه را برای زمان مشخص رزرو می‌کند.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_email": {"type": "string", "description": "آدرس ایمیل اتاق"},
                    "room_name": {"type": "string", "description": "نام اتاق"},
                    "subject": {"type": "string", "description": "موضوع جلسه"},
                    "start_time": {"type": "string", "description": "زمان شروع ISO 8601"},
                    "end_time": {"type": "string", "description": "زمان پایان ISO 8601"},
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "لیست ایمیل شرکت‌کنندگان (اختیاری)",
                    },
                },
                "required": ["room_email", "room_name", "subject", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "زمان و تاریخ فعلی به وقت تهران را برمی‌گرداند.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

SYSTEM_PROMPT = """تو دستیار هوشمند رزرو اتاق جلسه در سازمان یکتانت هستی.
وظیفه‌ات کمک به کاربران برای رزرو اتاق‌های جلسه از طریق تلگرام است.
به فارسی پاسخ بده. صادق و مودب باش.
اگر کاربر زمان مبهمی گفت (مثل «فردا» یا «ساعت ۳») از get_current_time استفاده کن تا زمان دقیق را محاسبه کنی.
قبل از رزرو حتماً availability اتاق را بررسی کن.
پس از رزرو موفق، تأییدیه کامل با جزئیات جلسه به کاربر نشان بده."""


async def run_booking_agent(
    username: str,
    password: str,
    conversation: list[dict],
) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(conversation)

    while True:
        response = await _client.chat.completions.create(
            model=config.REQUESTY_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=2048,
        )

        choice = response.choices[0]
        messages.append(choice.message.model_dump())

        if choice.finish_reason == "stop" or not choice.message.tool_calls:
            return choice.message.content or ""

        # Execute tool calls
        for tool_call in choice.message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            result = await _execute_tool(username, password, fn_name, fn_args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })


async def _execute_tool(username: str, password: str, name: str, inputs: dict) -> Any:
    if name == "get_current_time":
        now = datetime.now(TEHRAN_TZ)
        return {
            "current_time": now.isoformat(),
            "day_of_week": _persian_day(now.weekday()),
            "formatted": now.strftime("%Y-%m-%d %H:%M"),
        }

    if name == "get_available_rooms":
        rooms = await exchange.get_room_lists(username, password)
        return {"rooms": rooms}

    if name == "check_room_availability":
        start = datetime.fromisoformat(inputs["start_time"]).replace(tzinfo=TEHRAN_TZ)
        end = datetime.fromisoformat(inputs["end_time"]).replace(tzinfo=TEHRAN_TZ)
        available = await exchange.check_room_availability(
            username, password, inputs["room_email"], start, end
        )
        return {"available": available, "room_email": inputs["room_email"]}

    if name == "book_room":
        start = datetime.fromisoformat(inputs["start_time"]).replace(tzinfo=TEHRAN_TZ)
        end = datetime.fromisoformat(inputs["end_time"]).replace(tzinfo=TEHRAN_TZ)
        event_id = await exchange.book_room(
            username=username,
            password=password,
            room_email=inputs["room_email"],
            room_name=inputs["room_name"],
            subject=inputs["subject"],
            start=start,
            end=end,
            attendees=inputs.get("attendees", []),
        )
        return {
            "success": True,
            "event_id": event_id,
            "room": inputs["room_name"],
            "subject": inputs["subject"],
            "start": inputs["start_time"],
            "end": inputs["end_time"],
        }

    return {"error": f"ابزار ناشناخته: {name}"}


def _persian_day(weekday: int) -> str:
    days = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
    return days[weekday]
