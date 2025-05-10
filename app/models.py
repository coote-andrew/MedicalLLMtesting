from app import db
from datetime import datetime

class Investigation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Investigation {self.name}>'

class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    history = db.Column(db.Text, nullable=True)
    problem_list = db.Column(db.Text, nullable=True)
    recommended_questions = db.Column(db.Text, nullable=True)
    recommended_investigations = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    
    def __repr__(self):
        return f'<MedicalRecord {self.id}>'

class ModelConfig(db.Model):
    """Configuration for a specific LLM model"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Display name for the tab
    model_type = db.Column(db.String(20), nullable=False, default="ollama")  # "ollama" or "openai"
    model_name = db.Column(db.String(100), nullable=False)  # Actual model name (llama3.2, gpt-4, etc)
    api_key = db.Column(db.String(200), nullable=True)  # For OpenAI API
    system_prompt = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    position = db.Column(db.Integer, default=0)  # Order in the tabs
    last_processing_time_ms = db.Column(db.Integer, default=0)
    
    # Results
    recommended_questions = db.Column(db.Text, nullable=True)
    recommended_investigations = db.Column(db.Text, nullable=True)
    problem_list = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<ModelConfig {self.name} ({self.model_type}:{self.model_name})>'

class LLMConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    update_frequency = db.Column(db.Integer, default=100)  # Update every X words
    update_on_newline = db.Column(db.Boolean, default=True)  # Update on new line
    line_count_before_update = db.Column(db.Integer, default=2)  # Number of lines to wait before updating
    model_name = db.Column(db.String(100), default="llama3.2")  # Legacy field
    system_prompt = db.Column(db.Text, default="""You are a medical AI assistant. 
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
}""")
    
    def __repr__(self):
        return f'<LLMConfig {self.id}>'

class QueryLog(db.Model):
    """Model to store all query content and LLM responses"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    query_text = db.Column(db.Text, nullable=False)  # Patient history text
    model_type = db.Column(db.String(20), nullable=False, default="ollama")  # Type of model
    model_name = db.Column(db.String(100), nullable=False)  # Model used
    recommended_questions = db.Column(db.Text, nullable=True)  # Generated questions
    recommended_investigations = db.Column(db.Text, nullable=True)  # Generated investigations
    problem_list = db.Column(db.Text, nullable=True)  # Generated problem list
    raw_response = db.Column(db.Text, nullable=True)  # Raw LLM response
    processing_time_ms = db.Column(db.Integer, nullable=True)  # Processing time in milliseconds
    error = db.Column(db.Text, nullable=True)  # Any error message
    
    def __repr__(self):
        return f'<QueryLog {self.id} - {self.timestamp}>' 