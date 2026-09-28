from flask import Blueprint, request, jsonify, session
from extensions import db
from models import Product, Order, User
from flask_login import current_user
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
load_dotenv()
import json

chatbot_bp = Blueprint('chatbot', __name__)

# System prompt to give the bot personality and context
SYSTEM_PROMPT = """
You are 'AgroBot', the friendly and helpful AI assistant for AgroMart, an online marketplace for agricultural products (seeds, fertilizers, pesticides, irrigation tools).
Your goal is to help users find products, track orders, and provide agricultural advice.
Be concise, professional, and helpful. Use emojis occasionally (🌾, 🌱, 🚜).

Rules:
1. If a user asks for product prices or availability, use the 'Real Product Data' provided in the context.
2. If you don't know the answer, politely ask them to contact support at support@agromart.com.
3. Keep responses under 100 words unless detail is requested.
4. If the user is logged in, you can refer to them by their username.
5. Always provide prices in Indian Rupees (₹).
6. If anyone asks about the owner of this website, you must state that it is **Sahana N** and provide her professional links:
   - [LinkedIn](https://www.linkedin.com/in/sahana28)
   - [GitHub](https://github.com/sahana-coder28)
"""

def get_product_context(query):
    """Search for products mentioned in the query and returns a context string."""
    matched_products = []
    
    # Simple keyword search for products
    try:
        all_products = Product.query.all()
        for product in all_products:
            if product.name.lower() in query.lower():
                matched_products.append(f"- {product.name}: ₹{product.price} (Stock: {product.stock}, Category: {product.category})")
    except Exception:
        pass # Database might not be ready or same thread issue
    
    if matched_products:
        return "\nReal Product Data (Current Inventory):\n" + "\n".join(matched_products)
    return ""

def get_order_context():
    """Get the last few orders for the current user."""
    if current_user.is_authenticated and hasattr(current_user, 'orders'):
        try:
            orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(3).all()
            if orders:
                order_info = []
                for o in orders:
                    order_info.append(f"- Order #{o.id}: Status {o.status}, Total ₹{o.total_price}")
                return "\nUser's Recent Orders:\n" + "\n".join(order_info)
        except Exception:
            pass
    return ""

@chatbot_bp.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({"res"
        "ponse": "I didn't catch that. Could you please type something?"}), 400

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key or api_key == "":
        # Fallback response if API key is not configured
        if "owner" in user_message.lower():
            return jsonify({"response": "The owner of this website is **Sahana N**. 🌾\n\nYou can find more about her here:\n- [LinkedIn](https://www.linkedin.com/in/sahana28)\n- [GitHub](https://github.com/sahana-coder28)"})
        if "price" in user_message.lower() or "cost" in user_message.lower():
            return jsonify({"response": "I can help with prices! Please check our product catalog for real-time pricing, or ask me about a specific product after my Gemini brain is fully configured. 😉"})
        return jsonify({"response": "Hello! I'm AgroBot. I'm currently in 'offline mode' as my AI brain (Gemini API key) is not yet set up. How else can I assist you today? 🌾"})

    try:
        # Initialize the GenAI client
        client = genai.Client(api_key=api_key)
        
        # DEBUG: Help identify why the model isn't being found
        print(f"DEBUG: Using API key starting with: {api_key[:4]}...")
        
        # Attempt to list models to see what this key can actually see
        all_available_models = []
        try:
            print("DEBUG: Fetching available models for this key...")
            for m in client.models.list():
                # Correct attribute in new SDK is supported_actions
                if hasattr(m, 'supported_actions') and 'generateContent' in m.supported_actions:
                    all_available_models.append(m.name)
            print(f"DEBUG: Available models: {all_available_models}")
        except Exception as list_err:
            print(f"DEBUG: Could not list models: {str(list_err)}")

        # Prepare context (product prices, orders, etc.)
        product_context = get_product_context(user_message)
        order_context = get_order_context()
        user_info = f"User: {current_user.username}" if current_user.is_authenticated else "User: Guest"
        
        full_system_prompt = f"{SYSTEM_PROMPT}\n{user_info}\n{product_context}\n{order_context}"
        
        # Maintain session-based history
        if 'gemini_history_new' not in session:
            session['gemini_history_new'] = []
            
        history = []
        for msg in session['gemini_history_new'][-10:]:
            history.append(types.Content(
                role=msg['role'],
                parts=[types.Part(text=msg['parts'][0]['text'])]
            ))
            
        # ROBUST MODEL SELECTION
        # If we found models in the list, use them. Otherwise, try these defaults.
        model_fallbacks = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-flash-latest']
        if all_available_models:
            # Prepend found models to our search list, prioritizing the one we wanted
            if 'models/gemini-1.5-flash' in all_available_models:
                # Keep it at the top
                pass
            else:
                model_fallbacks = all_available_models + model_fallbacks

        last_error = None
        bot_response = None

        for target_model in model_fallbacks:
            try:
                print(f"DEBUG: Attempting chat with model: {target_model}")
                response = client.models.generate_content(
                    model=target_model,
                    contents=history + [types.Content(role='user', parts=[types.Part(text=user_message)])],
                    config=types.GenerateContentConfig(
                        system_instruction=full_system_prompt,
                        max_output_tokens=300,
                        temperature=0.7
                    )
                )
                bot_response = response.text
                if bot_response:
                    break # Success!
            except Exception as e:
                last_error = e
                print(f"DEBUG: Model {target_model} failed: {str(e)}")
                continue # Try next model

        if not bot_response:
            raise last_error # Re-raise the last error if all fallbacks failed

        # Update history
        session['gemini_history_new'].append({"role": "user", "parts": [{"text": user_message}]})
        session['gemini_history_new'].append({"role": "model", "parts": [{"text": bot_response}]})
        session.modified = True
        
        return jsonify({"response": bot_response})
        
    except Exception as e:
        # LOG THE FULL ERROR TO TERMINAL FOR DEBUGGING
        import traceback
        print("=== CHATBOT ERROR DETAILS ===")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        traceback.print_exc()
        print("=============================")
        
        # Graceful fallback for the user
        return jsonify({
            "response": "I'm having a little trouble connecting to my Gemini brain right now. 🤖 Please check your API key in the .env file and ensure your internet connection is stable!"
        })

@chatbot_bp.route('/chat/reset', methods=['POST'])
def reset_chat():
    session.pop('gemini_history_new', None)
    return jsonify({"status": "success"})
