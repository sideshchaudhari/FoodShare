from flask import Blueprint, render_template, request, jsonify
from app.utils.chatbot_engine import get_bot_response

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/donor/chatbot')


@chatbot_bp.route('/')
def chatbot_page():
    return render_template('donor/chatbot.html')


@chatbot_bp.route('/message', methods=['POST'])
def chatbot_message():
    user_msg = request.json.get("message")

    bot_reply = get_bot_response(user_msg)

    return jsonify({"reply": bot_reply})