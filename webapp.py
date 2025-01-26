from openai import OpenAI
from flask import Flask, render_template, request, jsonify
import os
from typing import List, Dict
import json
from datetime import datetime
import httpx

"""
Contact Center Support Application 

A Flask application providing real-time support for call center agents using LLM capabilities.
Key features:
- Customer identification from conversation
- Query classification (technical/promotional)
- Contextual response generation
- Conversation summarization
- Call logging and metrics tracking

TODO:
1. Port sentiment analysis from frontend to backend:
  - Create sentiment payload handling for both CML and AI inference service locations
  - Add sentiment route and task manager method
  - Modify frontend to use new endpoint

2. Externalize prompts for easy modification:
  - Move all LLM prompts to config files or vector DB
  - Add prompt management interface
  - Enable dynamic prompt updates for new use cases
"""

PORT = os.getenv('CDSW_APP_PORT', '8090')
CALL_LOG_FILE = 'call_log.json'
CUSTOMERS_FILE = 'customers.json'  # Add reference to customers file

app = Flask(__name__)


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
    def get_customer_info(self, text: str) -> dict:
        print('starting function build prompt')
        client = self.chat_clients['customer_info']
        print('client created')
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
    Respond in JSON format with:
    {{
        "queryType": "TECHNICAL" or "PROMOTIONAL",
        "confidence": 0.0-1.0
    }}
    
    Query: '{text}'"""
        
        response = client.chat(prompt)
        return json.loads(response)

    def get_ai_help(self, text: str, state: str, account_id: str) -> dict:
        client = self.chat_clients['technical' if state == "HANDLING_TECHNICAL" else 'promotional']
        
        base_prompt = """You are helping a call center worker for a telco company called airwave. Keep responses concise and focused."""
        
        if state == "HANDLING_TECHNICAL":
            prompt = f"""{base_prompt} You are handling a technical support query. 
            Provide step-by-step troubleshooting suggestions. Keep responses short and clear. 
            After 3 exchanges without resolution, suggest transfer to a technical specialist.
            Query: '{text}'"""
        else:
            prompt = f"""{base_prompt} Help explain the benefits and answer any questions.
            After 3 exchanges, suggest transfer to a sales specialist.
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

# Initialize manager
task_manager = TaskManager()

def load_customer_data():
    """Load customer data from JSON file"""
    try:
        with open(CUSTOMERS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Warning: Could not load {CUSTOMERS_FILE}")
        return {}

def init_call_log():
    """Initialize the call log file if it doesn't exist"""
    if not os.path.exists(CALL_LOG_FILE):
        with open(CALL_LOG_FILE, 'w') as f:
            json.dump({"calls": []}, f)

def log_call(caller_name, account_id, summary, call_type, overall_sentiment,queue_time_seconds):
             
    """Log a call to the JSON file with enhanced fields"""
    try:
        with open(CALL_LOG_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"calls": []}
    
    # Load customer data to get profile type and churn risk
    customers = load_customer_data()
    customer_info = customers.get(account_id, {})
    
    call_record = {
        # Basic fields
        "caller_name": caller_name,
        "account_id": account_id,
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
        
        # Call specific fields
        "call_type": call_type,
        "overall_sentiment": float(overall_sentiment),
       # "call_duration_minutes": int(call_duration_minutes),
        "queue_time_seconds": int(queue_time_seconds),
        
        # Customer profile fields
        "customer_profile_type": customer_info.get('profile_type', 'unknown'),
        "churn_risk": customer_info.get('churn_risk', 'unknown')
    }
    
    data["calls"].append(call_record)
    
    with open(CALL_LOG_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    return call_record

## App routing 

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

@app.route("/log_call", methods=['POST'])
def handle_call_log():
    """Handle the call logging POST request with enhanced fields"""
    print("Received call log request")  
    data = request.json
    print("Request data:", data)  # Add this
    
    # Validate call_type
    call_type = data.get('call_type')
    print('call type is : ',call_type)
    if call_type not in ['technical', 'promotional']:
        return jsonify({
            "status": "error",
            "message": "Invalid call_type. Must be 'technical' or 'promotional'"
        }), 400
    
    try:
        call_record = log_call(
            data.get('caller_name'),
            data.get('account_id'),
            data.get('summary'),
            call_type,
            data.get('overall_sentiment', 0.0),
           # data.get('call_duration_minutes', 0),
            data.get('queue_time_seconds', 0)
        )
        return jsonify({"status": "success", "record": call_record})
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    init_call_log()  # Initialize the log file when starting the app
    app.run(host='127.0.0.1', port=PORT)