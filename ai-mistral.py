import json
from datetime import datetime
import cml.data_v1 as cmldata
import os
import requests



# Model endpoint and access key for local Mistral
MODEL_ENDPOINT = "https://modelservice.ml-db89c6fb-96d.se-sandb.a465-9q4k.cloudera.site/model"
MODEL_ACCESS_KEY = "m1uiflisr7avf51gpwekkf96fjansw61"  # You might want to move this to .env file

def is_valid_date(date_str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

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
    
    elif task in ['ai_help', 'summarize']:
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

        # raw_response =  response.json()['response']['prediction']['response']
        # print('inference made')
        # raw_response = str(response.json()['response']['prediction']['response'])
        # print('Full response:', raw_response)  # For debugging

        raw_response = response.json()['response']['prediction']['response']
        print('raw_response',raw_response)
        result = str(raw_response)
        print('result',result)
        
        # Extract relevant content based on task and user_text
        return get_response_content(result, task, user_text)
        
    except Exception as e:
        print(f"Error calling Mistral model: {e}")
        return str(e)

def predict(data: dict[str, str]) -> dict:
    
    if not isinstance(data, dict):
        raise TypeError("data must be a dictionary")
    if "text" not in data:
        raise TypeError("data must contain a key of 'text'")
    if "task" not in data:
        raise TypeError("data must contain a key of 'task'")

    task = data['task']
    text = data["text"]

    print('task is',task)
    
    if task == 'ai_help':
        print('kicking off get ai help logic')
        system_prompt = """You are helping a call center worker for a telco company called airwave. You will receive the user text content, which will include the call center worker and the customers spoken words converted to text. You are called upon when the call center agent needs some sort of help, like details about the available products or suggestions for troubleshooting etc. It is your job to provide helpful suggestions. Make sure they are short so the call center worker can easily look at them and read them out to the customer. Do not include multiple suggestions, just one with enough information that the call center agent can use.

The company currently has 3 products:

AirSpeed Advanced:
- Special Offer € 45/month (€ 60 after 3 months)
- Up to 70 Mbps / 7 Mbps
- 12 Month contract
- FREE Fritzbox Router
- € 150 installation fee
- Optional Home Phone Service

AirSpeed Plus:
- Special Offer € 35/month (€ 50 after 3 months)
- Up to 50 Mbps / 5 Mbps
- 12 Month contract
- FREE Fritzbox Router
- € 150 installation fee
- Optional Home Phone Service

AirSpeed Home:
- Special Offer € 25/month (€ 40 after 3 months)
- Up to 30 Mbps / 3 Mbps
- 12 Month contract
- FREE Fritzbox Router
- € 150 installation fee
- Optional Home Phone Service

Note: 5% discount available for 2-year contracts (only for churn risk 1-2 customers or very negative conversations)."""
        
        response_text = get_mistral_response(system_prompt, text,temperature =1, task=task)
        output = {"recommendationText": response_text}

    elif task == 'summarize':
        print('kicking off summarize logic')
        system_prompt = """You are helping a call center worker for a telco company called airwave. Summarize the conversation provided, keeping it as short as possible while including all relevant information about the interaction, any products discussed, and any decisions made. Be concise but comprehensive."""
        
        response_text = get_mistral_response(system_prompt, text,temperature =1, task=task)
        output = {"recommendationText": response_text}

    elif task == 'getCustomerInfo':
        print('kicking off get cust info logic')
        system_prompt = """You are a helpful assistant for call center agents designed to analyze conversation text and extract customer information. Provide your answer in JSON format with these fields:
- "name": The customer's name
- "address": The customer's street and house number
- "dob": The customer's date of birth in YYYY-MM-DD format
If any information is missing, use empty strings for those fields."""
        
        response_text = get_mistral_response(system_prompt, text,temperature =1, task=task)
        print('response_text:', response_text)

        try:
            info = json.loads(response_text)
            
            # Initialize customerInfo with empty strings
            customer_info = {
                "name": "",
                "address": "",
                "date_of_birth": ""
            }
            
            # Track which fields are valid
            valid_fields = {
                "name": False,
                "address": False,
                "dob": False
            }
            
            # Check and populate each field individually
            if info.get("name"):
                customer_info["name"] = info["name"]
                valid_fields["name"] = True
                
            if info.get("address"):
                customer_info["address"] = info["address"]
                valid_fields["address"] = True
                
            if info.get("dob"):
                if is_valid_date(info["dob"]):
                    customer_info["date_of_birth"] = info["dob"]
                    valid_fields["dob"] = True
            
            # Check if all fields are valid (for foundCustomer flag)
            info_complete = all(valid_fields.values())
            
            # Create output with available information
            output = {
                "recommendationText": response_text,
                "foundCustomer": 1 if info_complete else 0,
                "customerInfo": customer_info
            }
            
            print('Valid fields:', valid_fields)
            print('Customer info:', customer_info)
            print('Complete:', info_complete)
            print('Output:', output)
            
        except json.JSONDecodeError as e:
            print('JSON decode error:', str(e))
            print('response_text',response_text)
            output = {
                "recommendationText": "{}",
                "error": "Invalid JSON response",
                "customerInfo": {
                    "name": "",
                    "address": "",
                    "date_of_birth": ""
                }
            }

    return output