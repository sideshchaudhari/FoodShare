def get_bot_response(message):
    msg = message.lower().strip()

    # ---------------- GREETING ----------------
    if msg in ["hi", "hello", "hey"]:
        return "👋 Hello! I am FoodShare Assistant. Ask me anything."

    # ---------------- HELP ----------------
    elif "help" in msg:
        return (
            "🆘 I can help you with:\n"
            "- donate food\n"
            "- ngo system\n"
            "- how it works\n"
            "- urgent food\n"
            "- status check"
        )

    # ---------------- DONATION ----------------
    elif "donate" in msg or "food" in msg:
        return (
            "🍱 Donation Steps:\n"
            "1. Go to Donor Dashboard\n"
            "2. Click Add Donation\n"
            "3. Enter food details\n"
            "4. Submit request\n"
            "NGO will be notified automatically."
        )

    # ---------------- NGO ----------------
    elif "ngo" in msg:
        return (
            "🏢 NGO System:\n"
            "- NGOs are matched by distance\n"
            "- Priority based on urgency\n"
            "- Expiry time is considered\n"
            "This ensures fast food delivery."
        )

    # ---------------- HOW IT WORKS ----------------
    elif "how" in msg and "work" in msg:
        return (
            "⚙ FoodShare Flow:\n"
            "Donor → Upload Food → System Match → NGO Pickup → Delivery ♻"
        )

    # ---------------- URGENT FOOD ----------------
    elif "urgent" in msg:
        return (
            "🚨 Urgent Mode:\n"
            "- Highest priority\n"
            "- Immediate NGO alert\n"
            "- Fast pickup arranged"
        )

    # ---------------- STATUS ----------------
    elif "status" in msg:
        return "📦 You can check donation status in your Donor Dashboard."

    # ---------------- LOGIN / ACCOUNT ----------------
    elif "login" in msg:
        return "🔐 Login using your registered email and password."

    # ---------------- THANK YOU ----------------
    elif "thank" in msg:
        return "😊 You're welcome! Happy to help."

    # ---------------- DEFAULT ----------------
    else:
        return (
            "🤖 I didn't understand that.\n\n"
            "Try asking:\n"
            "- How to donate food?\n"
            "- NGO system\n"
            "- How it works\n"
            "- urgent food help"
        )