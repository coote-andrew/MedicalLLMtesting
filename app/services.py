from app import db
from app.models import Investigation, LLMConfig, QueryLog, ModelConfig
import json
import requests
import traceback
import time
from datetime import datetime
import openai

# Ollama API client for LLM integration
class OllamaClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
        
    def generate(self, prompt, model="llama3.2", system="", format="json"):
        """
        Generate text from Ollama API with proper JSON formatting
        """
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "system": system,
                "format": format,
                "stream": False
            }
            
            print("PAYLOAD***", payload)
            response = requests.post(self.api_url, json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Exception in Ollama API call: {str(e)}")
            traceback.print_exc()
            return None

# OpenAI API client
class OpenAIClient:
    def __init__(self):
        self.client = None
    
    def set_api_key(self, api_key):
        self.client = openai.OpenAI(api_key=api_key)
    
    def generate(self, prompt, model="gpt-3.5-turbo", system="", format="json"):
        """
        Generate text from OpenAI API with proper JSON formatting
        """
        if not self.client:
            raise ValueError("API key not set. Call set_api_key first.")
            
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"} if format == "json" else None
            )
            
            return {
                "response": response.choices[0].message.content,
                "model": model
            }
        except Exception as e:
            print(f"Exception in OpenAI API call: {str(e)}")
            traceback.print_exc()
            return None

# Create singleton clients
ollama_client = OllamaClient()
openai_client = OpenAIClient()

def process_medical_history_with_model(history_text, model_config):
    """
    Process medical history with a specific model configuration
    """
    # Track processing time
    start_time = time.time()
    error_message = None
    raw_response = None
    
    # Get all available investigations from the database
    available_investigations = Investigation.query.all()
    investigation_list = "\n".join([f"- {inv.name}" for inv in available_investigations])
    
    # Format the prompt with history and available investigations
    prompt = f"""
Patient History:
{history_text}

Available Investigations:
{investigation_list}

Based on this patient history, provide recommendations.
"""
    
    result = None
    
    try:
        # Call appropriate API based on model type
        if model_config.model_type == "ollama":
            response = ollama_client.generate(
                prompt=prompt,
                model=model_config.model_name,
                system=model_config.system_prompt,
                format="json"
            )
        elif model_config.model_type == "openai":
            # Set API key (refreshed in case it was updated)
            openai_client.set_api_key(model_config.api_key)
            response = openai_client.generate(
                prompt=prompt,
                model=model_config.model_name,
                system=model_config.system_prompt,
                format="json"
            )
        else:
            error_message = f"Unsupported model type: {model_config.model_type}"
            print(error_message)
            return mock_llm_process(history_text, available_investigations), error_message, None, 0
        
        if response and 'response' in response:
            raw_response = response['response']
            try:
                # Parse the JSON response
                llm_response = json.loads(raw_response)
                
                # Ensure required fields exist and convert any lists or objects to strings
                recommended_questions = llm_response.get("recommended_questions", "")
                recommended_investigations = llm_response.get("recommended_investigations", "")
                problem_list = llm_response.get("problem_list", "")
                
                # Convert to strings if they are not already
                if isinstance(recommended_questions, list):
                    recommended_questions = "\n".join(recommended_questions)
                elif not isinstance(recommended_questions, str):
                    recommended_questions = json.dumps(recommended_questions)
                    
                if isinstance(recommended_investigations, list):
                    recommended_investigations = "\n".join(recommended_investigations)
                elif not isinstance(recommended_investigations, str):
                    recommended_investigations = json.dumps(recommended_investigations)
                    
                if isinstance(problem_list, list):
                    # Handle list of objects or strings
                    if problem_list and isinstance(problem_list[0], dict):
                        problem_items = []
                        for item in problem_list:
                            code = item.get("ICD10 Code", "")
                            desc = item.get("Problem Description", "")
                            problem_items.append(f"{code} - {desc}")
                        problem_list = "\n".join(problem_items)
                    else:
                        problem_list = "\n".join(problem_list)
                elif not isinstance(problem_list, str):
                    problem_list = json.dumps(problem_list)
                
                result = {
                    "recommended_questions": recommended_questions,
                    "recommended_investigations": recommended_investigations,
                    "problem_list": problem_list
                }
            except json.JSONDecodeError:
                error_message = "Failed to parse JSON response from LLM"
                print(error_message)
                # Return a fallback response
                result = mock_llm_process(history_text, available_investigations)
        else:
            error_message = "Invalid or empty response from API"
            print(error_message)
            result = mock_llm_process(history_text, available_investigations)
    except Exception as e:
        error_message = f"Error processing with {model_config.model_type} model: {str(e)}"
        print(error_message)
        traceback.print_exc()
        # Fall back to mock response
        result = mock_llm_process(history_text, available_investigations)
    
    # Calculate processing time
    end_time = time.time()
    processing_time_ms = int((end_time - start_time) * 1000)
    
    # Update the model config with the results and processing time
    model_config.recommended_questions = result.get("recommended_questions", "")
    model_config.recommended_investigations = result.get("recommended_investigations", "")
    model_config.problem_list = result.get("problem_list", "")
    model_config.last_processing_time_ms = processing_time_ms
    db.session.commit()
    
    return result, error_message, raw_response, processing_time_ms

def process_medical_history(history_text):
    """
    Process medical history with all active models
    """
    # Get all active models or use default if none
    model_configs = ModelConfig.query.filter_by(is_active=True).order_by(ModelConfig.position).all()
    
    # If no models are configured, use the default configuration
    if not model_configs:
        config = LLMConfig.query.first()
        if not config:
            config = LLMConfig()
            db.session.add(config)
            db.session.commit()
        
        # Create default model config from legacy config
        default_model = ModelConfig(
            name="Default",
            model_type="ollama",
            model_name=config.model_name,
            system_prompt=config.system_prompt,
            position=0,
            is_active=True
        )
        db.session.add(default_model)
        db.session.commit()
        model_configs = [default_model]
    
    main_result = None
    
    # Process with each model
    for model_config in model_configs:
        result, error_message, raw_response, processing_time_ms = process_medical_history_with_model(
            history_text, model_config
        )
        
        # Log this query
        query_log = QueryLog(
            timestamp=datetime.utcnow(),
            query_text=history_text,
            model_type=model_config.model_type,
            model_name=model_config.model_name,
            recommended_questions=result.get("recommended_questions", ""),
            recommended_investigations=result.get("recommended_investigations", ""),
            problem_list=result.get("problem_list", ""),
            raw_response=raw_response,
            processing_time_ms=processing_time_ms,
            error=error_message
        )
        db.session.add(query_log)
        db.session.commit()
        
        # First result becomes the main one (for backward compatibility)
        if main_result is None:
            main_result = result
    
    return main_result

# Mock LLM response - used as fallback if API fails
def mock_llm_process(history_text, available_investigations):
    """
    Mock LLM processing as a fallback
    """
    # Very basic mock response
    investigation_names = [inv.name for inv in available_investigations]
    investigation_list = "\n- ".join(investigation_names[:3]) if investigation_names else "No investigations available"
    
    return {
        "recommended_questions": "- Ask about duration of symptoms\n- Ask about fever\n- Ask about previous medical history",
        "recommended_investigations": f"- {investigation_list}",
        "problem_list": "R50.9 - Fever, unspecified\nR07.0 - Pain in throat"
    }

def init_services():
    """Initialize services and seed data"""
    # Add some initial investigations if none exist
    if Investigation.query.count() == 0:
        initial_investigations = [
            "Full Blood Count (FBC)",
            "Urea Electrolytes Creatinine (UEC)",
            "Liver Function Tests (LFT)",
            "Thyroid Function Tests (TFT)",
            "Urinalysis",
            "Chest X-ray",
            "Electrocardiogram (ECG)",
            "CT Scan",
            "MRI",
            "Theatre request"
        ]
        
        for inv_name in initial_investigations:
            investigation = Investigation(name=inv_name)
            db.session.add(investigation)
        
        db.session.commit()
        
    # Create default LLM config if none exists
    if LLMConfig.query.count() == 0:
        default_config = LLMConfig(
            update_frequency=100,
            update_on_newline=True,
            line_count_before_update=2,
            model_name="llama3.2",
            system_prompt="""You are a medical AI assistant. 
Based on the patient history provided, you will:
1. Suggest questions to ask the patient
2. Recommend physical examination components
3. Suggest relevant investigations from the available list only
4. Create a problem list with appropriate ICD-10 codes

Format your response in JSON with the following structure:
{
  "recommended_questions": "- Question 1\\n- Question 2\\n- Question 3",
  "recommended_investigations": "- Investigation 1\\n- Investigation 2",
  "problem_list": "ICD10 Code - Problem Description\\nICD10 Code - Problem Description"
}"""
        )
        db.session.add(default_config)
        db.session.commit()
    
    # Create default model configs if none exist
    if ModelConfig.query.count() == 0:
        # Get the default configuration
        config = LLMConfig.query.first()
        
        # Create Ollama model
        ollama_model = ModelConfig(
            name="Ollama: Llama3",
            model_type="ollama",
            model_name="llama3.2",
            system_prompt=config.system_prompt,
            position=0,
            is_active=True
        )
        db.session.add(ollama_model)

        ollama_model2 = ModelConfig(
            name="Ollama: Gemma3",
            model_type="ollama",
            model_name="gemma3:12b",
            system_prompt=config.system_prompt,
            position=1,
            is_active=True
        )
        db.session.add(ollama_model2)
        
        # Create OpenAI model (inactive by default)
        openai_model = ModelConfig(
            name="OpenAI: GPT-4.1",
            model_type="openai",
            model_name="gpt-4.1",
            system_prompt=config.system_prompt,
            position=2,
            is_active=False,
            api_key="" 
        )
        db.session.add(openai_model)
        
        db.session.commit()
        
    print("Database seeded with initial data.") 