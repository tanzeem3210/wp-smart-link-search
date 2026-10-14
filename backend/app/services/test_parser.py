
from app.services.chat_parser import parse_chat


sample = """\
12/31/25, 10:30 PM - Alex: Maths tutorial
12/31/25, 10:31 PM - Alex: https://www.youtube.com/watch?v=example123
12/31/25, 10:31 PM - Alex: https://www.youtube.com/watch?v=w-ukv1kUT94
12/31/25, 10:32 PM - Sam: I will watch this later
"""

messages = parse_chat(sample)

assert len(messages) == 4
assert messages[0]["sender"] == "Alex"
assert len(messages[1]["links"]) == 1
assert "youtube.com" in messages[1]["links"][0]

print("Parser test passed!")
print(f"Messages parsed: {len(messages)}")
print(f"Links extracted: {sum(len(m['links']) for m in messages)}")
