import anthropic
import requests
from dotenv import load_dotenv
import os
import time

load_dotenv()

anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
vapi_key = os.getenv("VAPI_API_KEY")
phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID")
my_phone = os.getenv("MY_PHONE")

conversation_history = []

system_prompt = """You are an AI assistant that helps users get information by making phone calls.

When a user asks you something that requires calling a business or person, respond with exactly this format:
MAKE_CALL: <question or topic to gather information about>

IMPORTANT: Only ever make ONE call. If the user asks about multiple topics, combine them all into a single MAKE_CALL. Never output more than one MAKE_CALL line.

Otherwise just answer conversationally. After a call transcript is given to you, extract all the key information and summarize it clearly and thoroughly for the user."""

def make_call(question):
    response = requests.post(
        "https://api.vapi.ai/call",
        headers={
            "Authorization": f"Bearer {vapi_key}",
            "Content-Type": "application/json"
        },
        json={
            "phoneNumberId": phone_number_id,
            "customer": {"number": my_phone},
            "assistant": {
                "firstMessage": f"Hey! I have some questions for you about: {question}",
                "model": {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "messages": [{"role": "system", "content": f"You are a friendly conversational assistant on a phone call. Your goal is to gather complete information about this topic: {question}. Ask natural follow up questions to get all the details. Keep the conversation going until you have thorough information — don't just accept one word answers, dig deeper. Once you have everything you need, thank them warmly and end the call."}]
                },
                "voice": {
                    "provider": "vapi",
                    "voiceId": "Elliot"
                }
            }
        }
    )
    call_data = response.json()
    call_id = call_data.get("id")
    print(f"\nCall started! Waiting for it to finish...")

    while True:
        time.sleep(5)
        status_response = requests.get(
            f"https://api.vapi.ai/call/{call_id}",
            headers={"Authorization": f"Bearer {vapi_key}"}
        )
        status_data = status_response.json()
        status = status_data.get("status")
        print(f"Call status: {status}")

        if status in ["ended", "failed"]:
            return status_data.get("transcript", "No transcript available")

print("AI Caller ready. Ask me anything that might require a phone call.")
print("Type 'quit' to exit.\n")

while True:
    user_input = input("You: ")

    if user_input.lower() == "quit":
        break

    conversation_history.append({"role": "user", "content": user_input})

    message = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=conversation_history
    )

    reply = next(block.text for block in message.content if hasattr(block, "text"))

    if reply.startswith("MAKE_CALL:"):
        question = reply.replace("MAKE_CALL:", "").strip()
        print(f"\nClaude: I'll call and ask about: '{question}'")
        transcript = make_call(question)
        print("\n--- RAW TRANSCRIPT ---")
        print(transcript)
        print("----------------------\n")

        conversation_history.append({"role": "assistant", "content": reply})
        conversation_history.append({"role": "user", "content": f"Here is the call transcript: {transcript}"})

        followup = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=conversation_history
        )

        final_reply = next(block.text for block in followup.content if hasattr(block, "text"))
        conversation_history.append({"role": "assistant", "content": final_reply})
        print(f"Claude: {final_reply}\n")

    else:
        conversation_history.append({"role": "assistant", "content": reply})
        print(f"\nClaude: {reply}\n")