from openai import OpenAI
from flask import Flask, render_template, request, jsonify
import os
from typing import List, Dict
import json
from datetime import datetime
import httpx

class ChatClient:
    """Handles communication with LLM hosted on AI inferencing services"""
    def __init__(self):
        if "OPENAI_BASE_URL" not in os.environ:
            raise ValueError("OPENAI_API_BASE environment variable must be set")
        if "OPENAI_MODEL_NAME" not in os.environ:
            raise ValueError("OPENAI_MODEL_NAME environment variable must be set")
            
        # Set up HTTP client
        if "CUSTOM_CA_STORE" not in os.environ:
            http_client = httpx.Client()
        else:
            http_client = httpx.Client(verify=os.environ["CUSTOM_CA_STORE"])
            
        # Load API key
        OPENAI_API_KEY = json.load(open("/tmp/jwt"))["access_token"]
        
        # Initialize OpenAI client
        self.client = OpenAI(
            base_url=os.environ["OPENAI_BASE_URL"],
            api_key=OPENAI_API_KEY,
            http_client=http_client,
        )
        self.conversation_history: List[Dict[str, str]] = []

    def chat(self, message: str) -> str:
        """Send a message and get response."""
        print('message is', message)
        self.conversation_history.append({"role": "user", "content": message})
    
        response = self.client.chat.completions.create(
            model=os.environ["OPENAI_MODEL_NAME"],
            messages=self.conversation_history,
            max_tokens = 150
        )
        
        complete_response = response.choices[0].message.content
        self.conversation_history.append({"role": "assistant", "content": complete_response})
        return complete_response

class TaskManager:
    def __init__(self):
        self.chat_clients = {
            'customer_info': ChatClient(),
            'technical': ChatClient(),
            'promotional': ChatClient(),
            'query_classifier': ChatClient(),
            'summarizer': ChatClient()
        }
        # Load plan and customer data
        self.promotions = self._load_json_file('promotions.json')
        self.customers = self._load_json_file('customers.json')

    def _load_json_file(self, filename: str) -> dict:
        """Helper method to load JSON files"""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return {}

    def get_customer_info(self, text: str) -> dict:
        client = self.chat_clients['customer_info']
        prompt = f"""You are a JSON extraction system. Extract customer information and return ONLY a JSON object.
Format must be exactly:
{{
    "account_id": "four digit account ID or empty string",
    "name": "full name or empty string"
}}
DO NOT add any extra text or conversation.

Here is the conversation to analyze: '{text}'"""
        
        response = client.chat(prompt)
        return json.loads(response)

    def classify_query(self, text: str) -> dict:
        client = self.chat_clients['query_classifier']
        prompt = f"""Determine if query is about technical support or promotions/sales.

PROMOTIONAL queries include:
- Asking about plan features or benefits
- Comparing plans
- Asking for recommendations ("best plan for...")
- Questions about pricing or offers
- Asking about upgrading or changing plans

TECHNICAL queries include:
- Current service problems or errors
- Device connection issues
- Service interruptions
- Poor performance of existing service
- Error messages

Note: If someone asks about "best plan" or "which plan", it's PROMOTIONAL even if they mention technical terms like streaming, gaming, or speed.

Return in JSON format:
{{
    "queryType": "TECHNICAL" or "PROMOTIONAL",
    "confidence": 0.0-1.0
}}

Query: '{text}'"""
        
        response = client.chat(prompt)
        return json.loads(response)

    def get_ai_help(self, text: str, state: str, account_id: str) -> dict:
        client = self.chat_clients['technical' if state == "HANDLING_TECHNICAL" else 'promotional']
        
        # Get customer and plan context
        customer = self.customers.get(account_id, {})
        current_plan_name = customer.get('current_plan', '')
        current_plan = None
        
        # Find current plan details
        for plan_type, plan_data in self.promotions.items():
            if plan_data['name'] == current_plan_name:
                current_plan = plan_data
                break

            
            # your goal is to be as helpful as possible. Listen to their repsonces to your responses very careful. Make sure you're not repeating yourself.
            # Provide some some basic first . Once you feel its appropriate you may offer them a different plan. They may ask you questions about the recommended plan. If they don't respond to the recommended plan or say no, do not keep bring the new plan up. 
        
        if state == "HANDLING_TECHNICAL":
            prompt = f"""Customer Current Plan: {json.dumps(current_plan)}

You are a helpful technical support assistant. Your priorities are:

1. Listen carefully to the customer's issue and acknowledge their attempts to resolve it
2. Ask clarifying questions if needed to fully understand the problem
3. Suggest new troubleshooting steps they haven't tried yet
4. Only mention plan upgrades if:
   - You've exhausted other solutions
   - The issue is clearly due to plan limitations
   - The customer expresses interest in additional features

Key guidelines:
- Don't repeat suggestions they've already tried
- Don't push plan upgrades if customer declines
- Remember previous interactions to avoid circular conversations
- Focus on solving their current problem first

If suggesting a plan upgrade becomes appropriate:
- Explain specifically how it would solve their issue
- Be prepared to answer questions about the new plan
- Respect their decision if they decline

Query: '{text}'"""

        else:
            prompt = f"""Customer Current Plan: {json.dumps(current_plan)}
You are an Airwave telecom support agent. Your approach:
1. Check current plan and conversation history before responding
2. Answer questions directly without greetings
3. Keep responses to 3-4 complete sentences
4. Address specific promotion questions using available plan data

Guidelines:
- Be concise and precise
- Don't repeat previous information
- Reference only valid promotions for their plan
- Skip pleasantries and introductions
Query: '{text}'"""
        response = client.chat(prompt)
        return {"recommendationText": response}

    def get_summary(self, text: str) -> dict:
        client = self.chat_clients['summarizer']
        prompt = f"""Analyze the conversation and return JSON with:
    {{
       "summary": "Concise but comprehensive summary",
       "overall_sentiment": float between 0-1
    }}
    Conversation: '{text}'"""
        
        response = client.chat(prompt)
        return json.loads(response)

# Initialize Flask app
app = Flask(__name__)

@app.route("/")
def main():
    return render_template('sko_demo_frontend-v2.html')

@app.route("/get_customer_info", methods=['POST'])
def handle_customer_info():
    try:
        print("Request data:", request.json)
        text = request.json.get('text')
        print("Text extracted:", text)
        result = task_manager.get_customer_info(text)
        print("Task manager result:", result)
        return jsonify(result)
    except Exception as e:
        print("Error:", str(e))
        print("Full error:", repr(e))
        return jsonify({"error": str(e)}), 500

@app.route("/classify_query", methods=['POST'])
def handle_query_classification():
    try:
        text = request.json.get('text')
        result = task_manager.classify_query(text)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_ai_help", methods=['POST'])
def handle_ai_help():
    try:
        data = request.json
        result = task_manager.get_ai_help(data['text'], data['currentState'], data.get('accountId', ''))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/summarize", methods=['POST'])
def handle_summary():
    try:
        text = request.json.get('text')
        result = task_manager.get_summary(text)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_customer_profile", methods=['GET'])
def get_customer_profile():
    try:
        account_id = request.args.get('account_id')
        if not account_id:
            return jsonify({"error": "Account ID required"}), 400
            
        profile = task_manager.customers.get(account_id)
        
        if profile:
            return jsonify(profile)
        else:
            return jsonify({"error": "Customer not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Initialize manager
task_manager = TaskManager()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=os.getenv('CDSW_APP_PORT', '8090'))