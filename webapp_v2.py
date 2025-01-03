from flask import Flask, render_template, request, jsonify  # Add request and jsonify
import requests
import os
import json
from datetime import datetime

PORT = os.getenv('CDSW_APP_PORT', '8090')
CALL_LOG_FILE = 'call_log.json'  # Define the log file path

MODEL_ENDPOINT = "https://modelservice.ml-100f4370-5ce.se-sandb.a465-9q4k.cloudera.site/model"
MODEL_ACCESS_KEY = "mc0viyv3fj7zgt8nxum88fwyjufujmz6"  # You might want to move this to .env file

app = Flask(__name__)

def init_call_log():
    """Initialize the call log file if it doesn't exist"""
    if not os.path.exists(CALL_LOG_FILE):
        with open(CALL_LOG_FILE, 'w') as f:
            json.dump({"calls": []}, f)

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
    
    # Get customer info
    customer = customers.get(account_id)
    if not customer:
        return None, promotions.get("default")
    
    # Get matching promotion
    promotion = promotions.get(customer["profile_type"], promotions.get("default"))
    return customer, promotion

def get_response_content(full_response, task, user_text):
    """Extract relevant content from model response based on task type"""

    print('task parameter is:',task)
    if task == 'getCustomerInfo':
        # Extract JSON content between curly braces
        start_idx = full_response.find('{')
        end_idx = full_response.rfind('}') + 1
        print('start and end index are:',start_idx,end_idx)
        if start_idx != -1 and end_idx > start_idx:
            print('got full response')
            return full_response[start_idx:end_idx]
        return '{}'
    
    #elif task in ['ai_help', 'summarize']:
    else:
        # Find position after the user's text
        pos = full_response.find(user_text)
        if pos != -1:
            # Get everything after the user's text
            return full_response[pos + len(user_text):].strip()
        return full_response

    return full_response

def get_mistral_response(system_prompt, user_text, temperature=0.7, max_tokens=500, task=None):
    """Helper function to get response from Mistral model"""
    llama_sys = f"<s>[INST]{system_prompt}[/INST]</s>"
    prompt = f"{llama_sys}\n[INST]{user_text}[/INST]"
    print('prompt built')
    try:
        print('building payload')
        payload = {
            "accessKey": MODEL_ACCESS_KEY,
            "request": {
                "prompt": prompt,
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "repetition_penalty": 1.0
            }
        }
        print('payload built')
        response = requests.post(
            MODEL_ENDPOINT, 
            data=json.dumps(payload), 
            headers={'Content-Type': 'application/json'}
        )
        raw_response = response.json()['response']['prediction']['response']
        print('raw_response',raw_response)
        result = str(raw_response)
        print('result',result)
        
        # Extract relevant content based on task and user_text
        return get_response_content(result, task, user_text)
        
    except Exception as e:
        print(f"Error calling Mistral model: {e}")
        return str(e)

def log_call(caller_name, account_id, summary):
    """Log a call to the JSON file"""
    try:
        with open(CALL_LOG_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"calls": []}
    
    call_record = {
        "caller_name": caller_name,
        "account_id": account_id,
        "timestamp": datetime.now().isoformat(),
        "summary": summary
    }
    
    data["calls"].append(call_record)
    
    with open(CALL_LOG_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    return call_record

@app.route("/")
def main():
    return render_template('sko_demo_frontend_v2.html')

@app.route("/proxy/model", methods=['POST'])
def proxy_model_request():
    data = request.json
    conversation_text = data.get('conversation_text')
    task = data.get('task')

    print('task',task)
    print('customer data',conversation_text)
    
    if task == 'getCustomerInfo':
        print('kicking off get cust info logic new app logic')
        # Construct the model payload

        system_prompt = """You are a helpful assistant for call center agents designed to analyze conversation text and extract customer information. Provide your answer in JSON format with these fields:
- "account_id": The customer's 4-digit account ID
- "name": The customer's full name
If any information is missing, use empty strings for those fields."""

        response_text = get_mistral_response(system_prompt, conversation_text,temperature =1, task=task)
        print('response_text:', response_text)

        try:
            info = json.loads(response_text)
            
            # Initialize customerInfo with empty strings
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
            if info.get("name"):
                customer_info["name"] = info["name"]
                valid_fields["name"] = True
                
            if info.get("account_id"):
                if len(info["account_id"]) == 4 and info["account_id"].isdigit():
                    customer_info["account_id"] = info["account_id"]
                    valid_fields["account_id"] = True
            
            # Check if all fields are valid (for foundCustomer flag)
            info_complete = all(valid_fields.values())
            
            # Create output with available information
            output = {
                "success": True,
                "response": {
                    "recommendationText": response_text,
                    "foundCustomer": 1 if info_complete else 0,
                    "customerInfo": customer_info
                }
            }            
            print('Valid fields:', valid_fields)
            print('Customer info:', customer_info)
            print('Complete:', info_complete)
            print('Output:', output)
    
        except json.JSONDecodeError as e:
            print('JSON decode error:', str(e))
            print('response_text',response_text)
            output = {
                "success": True,
                "response": {
                    "recommendationText": "{}",
                    "error": "Invalid JSON response",
                    "customerInfo": {
                        "name": "",
                        "account_id": ""
                    }
                }
            }

    elif task == 'classify_query':
        print('kicking off query classification logic')
        system_prompt = """You are helping a call center worker classify customer queries. Determine if the query is about technical support or about promotions/sales.
    
    Technical queries typically involve:
    - Network or connection issues
    - Device problems
    - Service not working
    - Setup help
    - Account access issues
    
    Promotional/Sales queries typically involve:
    - Questions about plans or pricing
    - Interest in upgrades
    - Special offers
    - New services
    - Package comparisons
    
    Respond in JSON format:
    {
        "queryType": "TECHNICAL" or "PROMOTIONAL",
        "confidence": 0.0-1.0
    }"""
    
        response_text = get_mistral_response(system_prompt, conversation_text,task=task)
        try:
            parsed_response = json.loads(response_text)
            output = {
    "success": True,
    "response": {
        "queryType": parsed_response["queryType"],
        "confidence": parsed_response["confidence"]
    }
}
            print('output :',output)

        except json.JSONDecodeError:
            output = {
                "success": False,
                "response": {
                    "queryType": "UNKNOWN",
                    "confidence": 0
                }
            }

    if task == 'ai_help':
        print('kicking off get ai help logic')
        current_state = data.get("currentState", "UNKNOWN")
        account_id = data.get("accountId", "")
        
        # Get customer info and promotion
        customer, promotion = get_customer_promotion(account_id)
        
        # Base system prompt
        base_prompt = """You are helping a call center worker for a telco company called airwave. Keep responses concise and focused."""
        
        if current_state == "HANDLING_TECHNICAL":
            system_prompt = base_prompt + """
            You are handling a technical support query. 
            Provide step-by-step troubleshooting suggestions. Keep responses short and clear. 
            After 3 exchanges without resolution, suggest transfer to a technical specialist.
            
            Customer Context:
            Name: {customer_name}
            Current Plan: {current_plan}
            """.format(
                customer_name=customer["name"] if customer else "Unknown",
                current_plan=customer["current_plan"] if customer else "Unknown"
            )
            
        elif current_state == "HANDLING_PROMOTIONAL":
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
                customer_context = """
                Customer not found. Using default promotion.
                
                Default Offer:
                {promotion_details}
                """.format(
                    promotion_details=json.dumps(promotion["details"], indent=2)
                )
            
            system_prompt = base_prompt + customer_context + """
            Based on the customer's profile and the available promotion, help explain the benefits 
            and answer any questions. After 3 exchanges, suggest transfer to a sales specialist."""
        
        else:
            system_prompt = base_prompt + """Determine if this is a technical or promotional query 
            and respond accordingly."""
        
        response_text = get_mistral_response(system_prompt, conversation_text, temperature=1, task=task)

        print('repsonses to customer', response_text)
        
        # Include customer and promotion info in response
        output = {"success": True, "response": 
            {"recommendationText": response_text,
            "customerInfo": customer if customer else {},
            "promotionInfo": promotion if promotion else {} }
        }
    
    return jsonify(output)

@app.route("/log_call", methods=['POST'])
def handle_call_log():
    """Handle the call logging POST request"""
    data = request.json
    call_record = log_call(
        data.get('caller_name'),
        data.get('account_id'),
        data.get('summary')
    )
    return jsonify({"status": "success", "record": call_record})

if __name__ == '__main__':
    init_call_log()  # Initialize the log file when starting the app
    app.run(host='127.0.0.1', port=PORT)