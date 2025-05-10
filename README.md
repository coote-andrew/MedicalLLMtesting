# Medical History LLM Assistant

A Flask-based application that assists with medical history taking by integrating with a local LLM through Ollama.

## Features

- Real-time medical history input
- LLM-powered recommendations for questions and exams to complete
- Recommended investigations based on a predefined list
- ICD-10 coded problem list
- Configurable LLM update settings (by word count or newline)
- Integration with Ollama API for local LLM processing
- Model selection and system prompt customization
- Query and response logging for audit and analysis

## Prerequisites

- Python 3.8 or higher
- [Ollama](https://ollama.ai/) installed and running locally

## Setup

1. Install Ollama (if not already installed):
   - Follow the instructions at https://ollama.ai/download
   - Ensure the Ollama service is running

2. Pull the models you want to use with Ollama:
   ```
   ollama pull llama3.2
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python run.py
   ```

5. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

## Usage

### Patient History
- Enter the patient's history in the text area on the left side.
- The LLM will automatically process the text and provide recommendations.

### LLM Output
- **Recommended Questions & Exams**: Questions to ask and examinations to perform
- **Recommended Investigations**: Suggested tests from the available investigations list
- **Problem List (ICD-10)**: List of problems with ICD-10 codes

### Investigations
- View the list of available investigations
- Add new investigations to the database

### LLM Configuration
- Select a different LLM model from the dropdown
- Customize the system prompt to guide the LLM's responses
- Set how often the LLM should process the text (by word count, by lines, and by inactivity timer)
- Enable/disable updating on newline entry
- OpenAI is setup but you need an developer account and API key to test this properly

### Query Logs
- All queries and responses are automatically saved to the database
- View detailed logs including:
  - Query text (patient history)
  - Model used
  - Processing time
  - Raw LLM response
  - Structured outputs (questions, investigations, problems)
- Access logs via the "View Query Logs" button on the main page

## Technical Notes

- The application connects to Ollama's API at http://localhost:11434 by default
- Structured JSON output is requested from the LLM to ensure consistent formatting
- If the Ollama API is unavailable, the system falls back to mock responses
- The application uses a local SQLite database to store investigations, configuration, and query logs

## Customization

You can further customize the Ollama integration by modifying:

1. The OllamaClient class in `app/services.py` to adjust connection parameters
2. The system prompt in the UI to provide different instructions to the LLM
3. The available_models list in `app/routes.py` to match your locally installed models 