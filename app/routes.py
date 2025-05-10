from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.models import Investigation, MedicalRecord, LLMConfig, QueryLog, ModelConfig
from app import db
from app.services import process_medical_history

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Get all investigations for display
    investigations = Investigation.query.all()
    
    # Get or create a config
    config = LLMConfig.query.first()
    if not config:
        config = LLMConfig()
        db.session.add(config)
        db.session.commit()
    
    # Get or create a medical record
    record = MedicalRecord.query.first()
    if not record:
        record = MedicalRecord(
            history="",
            problem_list="",
            recommended_questions="",
            recommended_investigations=""
        )
        db.session.add(record)
        db.session.commit()
    
    # Get all model configurations
    model_configs = ModelConfig.query.order_by(ModelConfig.position).all()
    if not model_configs:
        from app.services import init_services
        init_services()
        model_configs = ModelConfig.query.order_by(ModelConfig.position).all()
    
    # Get a list of available model types
    model_options = {
        "ollama": ["llama3.2", "mistral", "phi3", "llama3:8b"],
        "openai": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
    }
    
    return render_template('index.html', 
                           investigations=investigations,
                           record=record,
                           config=config,
                           model_configs=model_configs,
                           model_options=model_options)

@main_bp.route('/update_history', methods=['POST'])
def update_history():
    data = request.json
    history_text = data.get('history', '')
    
    # Get the current record or create one
    record = MedicalRecord.query.first()
    if not record:
        record = MedicalRecord()
        db.session.add(record)
    
    # Update the history
    record.history = history_text
    
    # Process with LLM
    result = process_medical_history(history_text)
    
    # Update recommendations without completely replacing previous data
    if result.get('recommended_questions'):
        record.recommended_questions = result.get('recommended_questions')
    
    if result.get('recommended_investigations'):
        record.recommended_investigations = result.get('recommended_investigations')
    
    if result.get('problem_list'):
        record.problem_list = result.get('problem_list')
    
    db.session.commit()
    
    # Get all model results
    model_results = []
    model_configs = ModelConfig.query.filter_by(is_active=True).order_by(ModelConfig.position).all()
    for model in model_configs:
        model_results.append({
            'id': model.id,
            'name': model.name,
            'model_type': model.model_type,
            'model_name': model.model_name,
            'recommended_questions': model.recommended_questions,
            'recommended_investigations': model.recommended_investigations,
            'problem_list': model.problem_list,
            'processing_time_ms': model.last_processing_time_ms
        })
    
    return jsonify({
        'success': True,
        'data': {
            'recommended_questions': record.recommended_questions,
            'recommended_investigations': record.recommended_investigations,
            'problem_list': record.problem_list,
            'model_results': model_results
        }
    })

@main_bp.route('/update_config', methods=['POST'])
def update_config():
    data = request.json
    
    config = LLMConfig.query.first()
    if not config:
        config = LLMConfig()
        db.session.add(config)
    
    if 'update_frequency' in data:
        config.update_frequency = int(data['update_frequency'])
    
    if 'update_on_newline' in data:
        config.update_on_newline = bool(data['update_on_newline'])
    
    if 'line_count_before_update' in data:
        config.line_count_before_update = int(data['line_count_before_update'])
    
    if 'model_name' in data:
        config.model_name = data['model_name']
        
    if 'system_prompt' in data:
        config.system_prompt = data['system_prompt']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'update_frequency': config.update_frequency,
            'update_on_newline': config.update_on_newline,
            'line_count_before_update': config.line_count_before_update,
            'model_name': config.model_name,
            'system_prompt': config.system_prompt
        }
    })

@main_bp.route('/models', methods=['GET', 'POST'])
def manage_models():
    if request.method == 'POST':
        data = request.form
        action = data.get('action')
        
        if action == 'add':
            # Add a new model
            new_model = ModelConfig(
                name=data.get('name', 'New Model'),
                model_type=data.get('model_type', 'ollama'),
                model_name=data.get('model_name', 'llama3.2'),
                system_prompt=data.get('system_prompt', ''),
                api_key=data.get('api_key', ''),
                position=ModelConfig.query.count(),
                is_active=bool(data.get('is_active', False))
            )
            db.session.add(new_model)
            db.session.commit()
            
        elif action == 'update':
            model_id = int(data.get('id'))
            model = ModelConfig.query.get(model_id)
            if model:
                model.name = data.get('name', model.name)
                model.model_type = data.get('model_type', model.model_type)
                model.model_name = data.get('model_name', model.model_name)
                model.system_prompt = data.get('system_prompt', model.system_prompt)
                model.is_active = 'is_active' in data
                
                # Only update API key if provided and not empty
                new_api_key = data.get('api_key', '')
                if new_api_key:
                    model.api_key = new_api_key
                
                db.session.commit()
                
        elif action == 'delete':
            model_id = int(data.get('id'))
            model = ModelConfig.query.get(model_id)
            if model:
                db.session.delete(model)
                db.session.commit()
                
        elif action == 'reorder':
            model_id = int(data.get('id'))
            direction = data.get('direction')
            model = ModelConfig.query.get(model_id)
            
            if model:
                if direction == 'up' and model.position > 0:
                    # Swap with the model above
                    other_model = ModelConfig.query.filter_by(position=model.position-1).first()
                    if other_model:
                        other_model.position, model.position = model.position, other_model.position
                        db.session.commit()
                elif direction == 'down':
                    # Swap with the model below
                    other_model = ModelConfig.query.filter_by(position=model.position+1).first()
                    if other_model:
                        other_model.position, model.position = model.position, other_model.position
                        db.session.commit()
        
        return redirect(url_for('main.index'))
    
    # GET request
    model_configs = ModelConfig.query.order_by(ModelConfig.position).all()
    model_options = {
        "ollama": ["llama3.2", "mistral", "phi3", "llama3:8b"],
        "openai": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
    }
    
    return render_template('models.html', 
                           model_configs=model_configs,
                           model_options=model_options)

@main_bp.route('/investigations', methods=['GET', 'POST'])
def manage_investigations():
    if request.method == 'POST':
        data = request.json
        name = data.get('name')
        
        if name:
            # Check if it already exists
            existing = Investigation.query.filter_by(name=name).first()
            if not existing:
                new_investigation = Investigation(name=name)
                db.session.add(new_investigation)
                db.session.commit()
                return jsonify({'success': True, 'id': new_investigation.id, 'name': name})
            return jsonify({'success': False, 'error': 'Investigation already exists'})
        
        return jsonify({'success': False, 'error': 'Name is required'})
    
    # GET request - return all investigations
    investigations = Investigation.query.all()
    return jsonify({
        'success': True,
        'data': [{'id': inv.id, 'name': inv.name} for inv in investigations]
    })

@main_bp.route('/logs')
def view_logs():
    # Get query logs ordered by timestamp (newest first)
    logs = QueryLog.query.order_by(QueryLog.timestamp.desc()).all()
    return render_template('logs.html', logs=logs)

@main_bp.route('/logs/<int:log_id>')
def view_log_detail(log_id):
    # Get specific log entry
    log = QueryLog.query.get_or_404(log_id)
    return render_template('log_detail.html', log=log) 