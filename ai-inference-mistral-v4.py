import json
from datetime import datetime
import httpx
from openai import OpenAI
import os
from typing import List, Dict

class ChatClient:
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
    
    def add_system_message(self, content: str):
        """Add a system message using Mistral's format."""
        # For Mistral, we store system content to combine with next user message
        self.system_content = content

    def chat(self, message: str) -> str:
    """Send a message and get response."""
    self.conversation_history.append({"role": "user", "content": message})
    
    response = self.client.chat.completions.create(
        model=os.environ["OPENAI_MODEL_NAME"],
        messages=self.conversation_history,
    )
    
    complete_response = response.choices[0].message.content
    self.conversation_history.append({"role": "assistant", "content": complete_response})
    return complete_response
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get the conversation history."""
        return self.conversation_history
    
    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []

def load_customer_data():
    try:
        with open('customers.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Customer data file not found")
        return {}

def load_promotions_data():
    try:
        with open('promotions.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Promotions data file not found")
        return {}

def get_customer_promotion(account_id):
    """Get customer info and matching promotion."""
    customers = load_customer_data()
    promotions = load_promotions_data()
    
    customer = customers.get(account_id)
    if not customer:
        return None, promotions.get("default")
    
    promotion = promotions.get(customer["profile_type"], promotions.get("default"))
    return customer, promotion

# Global chat clients for different tasks
chat_clients = {
    'technical': ChatClient(),
    'promotional': ChatClient(),
    'customer_info': ChatClient(),
    'query_classifier': ChatClient(),
    'summarizer': ChatClient()
}

def predict(data: dict[str, str]) -> dict:
    if not isinstance(data, dict):
        raise TypeError("data must be a dictionary")
    if "text" not in data:
        raise TypeError("data must contain a key of 'text'")
    if "task" not in data:
        raise TypeError("data must contain a key of 'task'")

    task = data['task']
    text = data["text"]
    current_state = data.get("currentState", "AWAITING_ID")
    
    print('task is', task)
    
        # Enforce account ID verification before allowing other tasks
    if task != 'getCustomerInfo' and current_state in ["INIT", "AWAITING_ID"]:
        return {
            "response": {
                "recommendationText": "Please provide your account ID before proceeding.",
                "error": "Account ID required",
                "customerInfo": {"name": "", "account_id": ""}
            },
            "success": False
        }

    if task == 'ai_help':
        account_id = data.get("accountId", "")
        customer, promotion = get_customer_promotion(account_id)
        
        # Select appropriate chat client based on state
        client_key = 'technical' if current_state == "HANDLING_TECHNICAL" else 'promotional'
        chat_client = chat_clients[client_key]
        
        # Clear history if this is a new conversation
        if len(chat_client.get_history()) == 0:
            base_prompt = """You are helping a call center worker for a telco company called airwave. Keep responses concise and focused."""
            
            if current_state == "HANDLING_TECHNICAL":
                system_content = base_prompt + f"""
                You are handling a technical support query. 
                Provide step-by-step troubleshooting suggestions. Keep responses short and clear. 
                After 3 exchanges without resolution, suggest transfer to a technical specialist.
                
                Customer Context:
                Name: {customer["name"] if customer else "Unknown"}
                Current Plan: {customer["current_plan"] if customer else "Unknown"}
                """
            else:
                # Build promotional context
                if customer:
                    customer_context = f"""
                    Customer Profile:
                    - Name: {customer["name"]}
                    - Current Plan: {customer["current_plan"]}
                    - Time with us: {customer["tenure_months"]} months
                    - Profile Type: {customer["profile_type"]}
                    - Churn Risk: {customer["churn_risk"]}
                    
                    Recommended Promotion: {promotion["name"]}
                    Monthly Cost: {promotion["details"]["monthly_cost"]}
                    
                    Key Features:
                    {chr(10).join("- " + feature for feature in promotion["details"]["plan_features"])}
                    
                    Special Offers:
                    {chr(10).join("- " + offer for offer in promotion["details"]["special_offers"])}
                    """
                else:
                    customer_context = f"""
                    Customer not found. Using default promotion.
                    Default Offer:
                    {json.dumps(promotion["details"], indent=2)}
                    """
                
                system_content = base_prompt + customer_context + """
                Based on the customer's profile and the available promotion, help explain the benefits 
                and answer any questions. After 3 exchanges, suggest transfer to a sales specialist."""
            
            chat_client.add_system_message(system_content)
        
        response_text = chat_client.chat(text)
        
        output = {
            "recommendationText": response_text,
            "customerInfo": customer if customer else {},
            "promotionInfo": promotion if promotion else {}
        }
        
        return {"response": output, "success": True}

    elif task == 'summarize':
        chat_client = chat_clients['summarizer']
        if len(chat_client.get_history()) == 0:
            system_content = """You are helping a call center worker for a telco company called Airwave. 
            Analyze the provided conversation and return a JSON object with two fields:
            1. "summary": A concise but comprehensive summary of the interaction
            2. "overall_sentiment": A float between 0 and 1 representing the overall sentiment
            
            Return your response in valid JSON format."""
            chat_client.add_system_message(system_content)
        
        response_text = chat_client.chat(text)
        
        try:
            response_data = json.loads(response_text)
            sentiment = float(response_data.get('overall_sentiment', 0.5))
            sentiment = max(0.0, min(1.0, sentiment))
            output = {
                "recommendationText": response_data.get('summary', ''),
                "overall_sentiment": sentiment
            }
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing model response: {e}")
            output = {
                "recommendationText": response_text,
                "overall_sentiment": 0.5
            }
        
        return {"response": output, "success": True}

    elif task == 'classify_query':
        chat_client = chat_clients['query_classifier']
        if len(chat_client.get_history()) == 0:
            system_content = """You are helping a call center worker classify customer queries.
            Determine if the query is about technical support or about promotions/sales.
            Respond in JSON format with queryType as "TECHNICAL" or "PROMOTIONAL" and confidence between 0.0-1.0."""
            chat_client.add_system_message(system_content)
        
        response_text = chat_client.chat(text)
        
        try:
            parsed_response = json.loads(response_text)
            output = {
                "queryType": parsed_response["queryType"],
                "confidence": parsed_response["confidence"]
            }
        except json.JSONDecodeError:
            output = {
                "queryType": "UNKNOWN",
                "confidence": 0
            }
        
        return {"response": output, "success": True}

    elif task == 'getCustomerInfo':
        chat_client = chat_clients['customer_info']
        if len(chat_client.get_history()) == 0:
            system_content = """You are a helpful assistant for call center agents designed to analyze conversation text and extract customer information. Provide your answer in JSON format with these fields:
- "account_id": The customer's 4-digit account ID
            
                Format must be exactly:
                {
                    "account_id": "four digit account ID or empty string",
                    "name": "full name or empty string"
                }
                DO NOT add any extra text or conversation.
                
                Example:
                Input: "Hi, my name is John Smith and my account number is 1234"
                Output: {
                    "account_id": "1234",
                    "name": "John Smith"
                }
                
                Input: "Hello, I'm Mary Jones"
                Output: {
                    "account_id": "",
                    "name": "Mary Jones"
                }"""
            
            chat_client.add_system_message(system_content)
        
        # Simplified: Removed redundant get_response_content call since we enforce JSON in prompt
        response_text = chat_client.chat(f"Extract customer information from: {text}")
        print('Raw model response:', response_text)
        
        try:
            parsed_info = json.loads(response_text)
            print('parsed customer info:', parsed_info)
            customer_info = {
               "account_id": "",
               "name": ""
           }
        
           # Track which fields are valid
            valid_fields = {
               "account_id": False,
               "name": False
           }
        
           # Check and populate each field individually
            if parsed_info.get("name"):
                customer_info["name"] = parsed_info["name"]
                valid_fields["name"] = True
               
            if parsed_info.get("account_id"):
                if len(parsed_info["account_id"]) == 4 and parsed_info["account_id"].isdigit():
                    customer_info["account_id"] = parsed_info["account_id"]
                    valid_fields["account_id"] = True
           
           # Check if all fields are valid (for foundCustomer flag)
            info_complete = all(valid_fields.values())
        
           # Create output with available information
            output = {
               "recommendationText": response_text,
               "foundCustomer": 1 if info_complete else 0,
               "customerInfo": customer_info
           }
           
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            output = {
               "recommendationText": "{}",
               "foundCustomer": 0,
               "customerInfo": {"name": "", "account_id": ""}
            }
           
        return {"response": output, "success": True}