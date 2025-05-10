document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const historyTextarea = document.getElementById('historyTextarea');
    const newInvestigationInput = document.getElementById('newInvestigationInput');
    const addInvestigationBtn = document.getElementById('addInvestigationBtn');
    const investigationsList = document.getElementById('investigationsList');
    const updateFrequency = document.getElementById('updateFrequency');
    const updateOnNewline = document.getElementById('updateOnNewline');
    const lineCountBeforeUpdate = document.getElementById('lineCountBeforeUpdate');
    const inactivityTimer = document.getElementById('inactivityTimer');
    const saveConfigBtn = document.getElementById('saveConfigBtn');

    // Configuration
    let config = {
        updateFrequency: parseInt(updateFrequency.value) || 100,
        updateOnNewline: updateOnNewline.checked,
        lineCountBeforeUpdate: parseInt(lineCountBeforeUpdate.value) || 2,
        inactivityTimer: parseInt(inactivityTimer.value) || 3
    };

    // Word count and timer variables
    let wordCount = 0;
    let typingTimer;
    let lastHistoryText = historyTextarea.value;
    let newlineCounter = 0;  // Count of new lines added since last update
    let lastLineCount = historyTextarea.value.split('\n').length;
    
    // Update the LLM output based on history text
    async function updateLLMOutput() {
        const historyText = historyTextarea.value;
        
        // Don't update if the text hasn't changed
        if (historyText === lastHistoryText) {
            return;
        }
        
        lastHistoryText = historyText;
        lastLineCount = historyText.split('\n').length;
        newlineCounter = 0;  // Reset the counter after update
        
        try {
            // Show loading state in all model tabs
            document.querySelectorAll('.questions-output').forEach(el => {
                el.textContent = "Processing...";
            });
            document.querySelectorAll('.investigations-output').forEach(el => {
                el.textContent = "Processing...";
            });
            document.querySelectorAll('.problems-output').forEach(el => {
                el.textContent = "Processing...";
            });
            
            const response = await fetch('/update_history', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ history: historyText })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update each model's output in its tab
                if (data.data.model_results && data.data.model_results.length > 0) {
                    data.data.model_results.forEach(model => {
                        // Find the outputs for this model
                        const questionsOutput = document.querySelector(`.questions-output[data-model-id="${model.id}"]`);
                        const investigationsOutput = document.querySelector(`.investigations-output[data-model-id="${model.id}"]`);
                        const problemsOutput = document.querySelector(`.problems-output[data-model-id="${model.id}"]`);
                        
                        // Update outputs if elements exist
                        if (questionsOutput && model.recommended_questions) {
                            questionsOutput.textContent = model.recommended_questions;
                        }
                        
                        if (investigationsOutput && model.recommended_investigations) {
                            investigationsOutput.textContent = model.recommended_investigations;
                        }
                        
                        if (problemsOutput && model.problem_list) {
                            problemsOutput.textContent = model.problem_list;
                        }
                    });
                }
            }
        } catch (error) {
            console.error('Error updating LLM output:', error);
            document.querySelectorAll('.questions-output').forEach(el => {
                el.textContent = "Error processing request.";
            });
            document.querySelectorAll('.investigations-output').forEach(el => {
                el.textContent = "Error processing request.";
            });
            document.querySelectorAll('.problems-output').forEach(el => {
                el.textContent = "Error processing request.";
            });
        }
    }
    
    // Function to count words in a string
    function countWords(text) {
        return text.trim().split(/\s+/).length;
    }
    
    // Check if the only change was adding an empty line
    function isOnlyEmptyLineAdded(oldText, newText) {
        // If text length difference is more than 2 characters, it's not just an empty line
        if (newText.length - oldText.length > 2) {
            return false;
        }
        
        // If the new text doesn't end with a newline, it's not adding an empty line
        if (!newText.endsWith('\n')) {
            return false;
        }
        
        // Count the number of trailing newlines in both texts
        const oldTrailingNewlines = (oldText.match(/\n+$/g) || [''])[0].length;
        const newTrailingNewlines = (newText.match(/\n+$/g) || [''])[0].length;
        
        // If the only difference is one more newline at the end, it's an empty line addition
        return newTrailingNewlines === oldTrailingNewlines + 1 && 
               oldText + '\n' === newText;
    }
    
    // Count the number of meaningful lines added (non-empty)
    function countMeaningfulLinesAdded(oldText, newText) {
        const oldLines = oldText.split('\n');
        const newLines = newText.split('\n');
        
        // If fewer lines than before, reset the counter
        if (newLines.length <= oldLines.length) {
            return 0;
        }
        
        // Count meaningful new lines (non-empty)
        let meaningfulNewLines = 0;
        for (let i = oldLines.length; i < newLines.length; i++) {
            if (newLines[i].trim().length > 0) {
                meaningfulNewLines++;
            }
        }
        
        return meaningfulNewLines;
    }
    
    // Event listener for textarea input
    historyTextarea.addEventListener('input', function() {
        // Clear any existing timer
        clearTimeout(typingTimer);
        
        const text = this.value;
        
        // Check if the only change was adding an empty line at the end or between paragraphs
        if (isOnlyEmptyLineAdded(lastHistoryText, text)) {
            // Just update the lastHistoryText without triggering LLM update
            lastHistoryText = text;
            return;
        }
        
        const currentWordCount = countWords(text);
        const currentLineCount = text.split('\n').length;
        let shouldUpdate = false;
        
        // Check if we have new lines since last check
        if (currentLineCount > lastLineCount) {
            // Add the number of meaningful new lines to our counter
            newlineCounter += countMeaningfulLinesAdded(lastHistoryText, text);
            
            // If we've reached the configured line count threshold, update
            if (newlineCounter >= config.lineCountBeforeUpdate) {
                shouldUpdate = true;
                newlineCounter = 0;  // Reset counter after update
            }
        }
        
        // Check if update should happen on word count threshold
        if (!shouldUpdate && currentWordCount - wordCount >= config.updateFrequency) {
            shouldUpdate = true;
            wordCount = currentWordCount;
        }
        
        // Check if update should happen on newline that contains actual content
        if (!shouldUpdate && config.updateOnNewline && 
            text.endsWith('\n') && 
            !lastHistoryText.endsWith('\n') &&
            !text.endsWith('\n\n') &&  // Don't trigger on double newlines (formatting)
            text.split('\n').slice(-2, -1)[0].trim().length > 0) { // Check if the previous line has content
            shouldUpdate = true;
        }
        
        if (shouldUpdate) {
            updateLLMOutput();
        } else {
            // Only set the inactivity timer if we haven't triggered an update
            // and the text has actually changed
            if (text !== lastHistoryText) {
                typingTimer = setTimeout(() => {
                    // Only update if the text hasn't changed since we set the timer
                    if (historyTextarea.value === text) {
                        updateLLMOutput();
                    }
                }, config.inactivityTimer * 1000);
            }
        }
        
        // Always update lastHistoryText and lastLineCount
        lastHistoryText = text;
        lastLineCount = currentLineCount;
    });
    
    // Event listener for adding a new investigation
    addInvestigationBtn.addEventListener('click', async function() {
        const name = newInvestigationInput.value.trim();
        
        if (!name) {
            return;
        }
        
        try {
            const response = await fetch('/investigations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name: name })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Add the new investigation to the list
                const li = document.createElement('li');
                li.className = 'list-group-item';
                li.textContent = name;
                investigationsList.appendChild(li);
                
                // Clear the input
                newInvestigationInput.value = '';
                
                // Update the LLM output
                updateLLMOutput();
            } else {
                alert(data.error || 'Failed to add investigation');
            }
        } catch (error) {
            console.error('Error adding investigation:', error);
        }
    });
    
    // Event listener for saving config
    saveConfigBtn.addEventListener('click', async function() {
        const newConfig = {
            update_frequency: parseInt(updateFrequency.value) || 100,
            update_on_newline: updateOnNewline.checked,
            line_count_before_update: parseInt(lineCountBeforeUpdate.value) || 2,
            inactivity_timer: parseInt(inactivityTimer.value) || 3
        };
        
        try {
            // Show saving indicator
            saveConfigBtn.textContent = 'Saving...';
            saveConfigBtn.disabled = true;
            
            const response = await fetch('/update_config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(newConfig)
            });
            
            const data = await response.json();
            
            if (data.success) {
                config = {
                    updateFrequency: newConfig.update_frequency,
                    updateOnNewline: newConfig.update_on_newline,
                    lineCountBeforeUpdate: newConfig.line_count_before_update,
                    inactivityTimer: newConfig.inactivity_timer
                };
                alert('Configuration saved successfully');
                
                // Reset the line counter
                newlineCounter = 0;
                
                // Update the LLM output with new settings
                updateLLMOutput();
            }
        } catch (error) {
            console.error('Error saving config:', error);
            alert('Error saving configuration');
        } finally {
            // Reset button
            saveConfigBtn.textContent = 'Save Configuration';
            saveConfigBtn.disabled = false;
        }
    });
}); 