import re

# Emoji-to-text mapping (expand as needed)
EMOJI_TO_TEXT = {
    "😀": ":grinning:", "😃": ":smiley:", "😄": ":smile:", "😁": ":grin:", "😆": ":laughing:", "😅": ":sweat_smile:",
    "😂": ":joy:", "🤣": ":rofl:", "😊": ":blush:", "😇": ":innocent:", "🙂": ":slight_smile:", "🙃": ":upside_down:",
    "😉": ":wink:", "😌": ":relieved:", "😍": ":heart_eyes:", "🥰": ":smiling_face_with_3_hearts:", "😘": ":kissing_heart:",
    "😗": ":kissing:", "😙": ":kissing_smiling_eyes:", "😚": ":kissing_closed_eyes:", "😋": ":yum:", "😜": ":stuck_out_tongue_winking_eye:",
    "😝": ":stuck_out_tongue_closed_eyes:", "😛": ":stuck_out_tongue:", "🤑": ":money_mouth:", "🤗": ":hugs:", "🤭": ":hand_over_mouth:",
    "🤫": ":shushing_face:", "🤔": ":thinking:", "🤐": ":zipper_mouth:", "🤨": ":raised_eyebrow:", "😐": ":neutral_face:",
    # Add more as needed
}

EMOJI_PATTERN = re.compile('|'.join(map(re.escape, EMOJI_TO_TEXT.keys())))

def emoji_to_text(s: str) -> str:
    """Replace all emojis in string with their text equivalents."""
    return EMOJI_PATTERN.sub(lambda m: EMOJI_TO_TEXT.get(m.group(0), m.group(0)), s)
