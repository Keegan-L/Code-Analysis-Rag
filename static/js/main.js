document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const uploadForm = document.getElementById('upload-form');
    const uploadStatus = document.getElementById('upload-status');
    const repositoryInfo = document.getElementById('repository-info');
    const repoSummary = document.getElementById('repo-summary');
    const chatSection = document.getElementById('chat-section');
    const chatMessages = document.getElementById('chat-messages');
    const queryInput = document.getElementById('query-input');
    const sendQueryButton = document.getElementById('send-query');
    const findOptimizationsButton = document.getElementById('find-optimizations');
    const suggestImprovementsButton = document.getElementById('suggest-improvements');
    const generateDocsButton = document.getElementById('generate-docs');
    const fileInput = document.getElementById('repository');

    // Handle file selection
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            showStatus('File selected: ' + fileInput.files[0].name, 'info');
        }
    });

    // Handle repository upload
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        
        try {
            showStatus('Uploading and processing repository...', 'info');
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showStatus('Repository processed successfully!', 'success');
                showRepositoryInfo(data);
                setupDocumentationGeneration();
            } else {
                showStatus(data.error || 'Error processing repository', 'error');
            }
        } catch (error) {
            showStatus('Error uploading repository: ' + error.message, 'error');
        }
    });

    // Handle query submission
    sendQueryButton.addEventListener('click', async () => {
        const query = queryInput.value.trim();
        if (!query) return;
        
        const repoId = sessionStorage.getItem('repo_id');
        if (!repoId) {
            addMessage('Error: No repository loaded. Please upload a repository first.', 'assistant');
            return;
        }
        
        addMessage(query, 'user');
        queryInput.value = '';
        
        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    query,
                    repo_id: repoId
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                addMessage(data.answer, 'assistant');
                
                // Show code references if any
                if (data.code_references && data.code_references.length > 0) {
                    data.code_references.forEach(ref => {
                        addCodeReference(ref);
                    });
                }
            } else {
                addMessage('Error: ' + (data.error || 'Failed to process query'), 'assistant');
            }
        } catch (error) {
            addMessage('Error: ' + error.message, 'assistant');
        }
    });

    // Handle optimization suggestions
    findOptimizationsButton.addEventListener('click', async () => {
        try {
            const response = await fetch('/optimize', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                addMessage(data.answer || 'No optimizations found', 'assistant');
            } else {
                addMessage('Error: ' + (data.error || 'Failed to find optimizations'), 'assistant');
            }
        } catch (error) {
            addMessage('Error: ' + error.message, 'assistant');
        }
    });

    // Handle improvement suggestions
    suggestImprovementsButton.addEventListener('click', async () => {
        try {
            const response = await fetch('/suggest', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                addMessage(data.answer || 'No suggestions found', 'assistant');
            } else {
                addMessage('Error: ' + (data.error || 'Failed to get suggestions'), 'assistant');
            }
        } catch (error) {
            addMessage('Error: ' + error.message, 'assistant');
        }
    });

    // Handle documentation generation
    function setupDocumentationGeneration() {
        if (generateDocsButton) {
            console.log('Found generate docs button');
            generateDocsButton.addEventListener('click', async () => {
                console.log('Generate docs button clicked');
                const repoId = sessionStorage.getItem('repo_id');
                console.log('Current repo_id:', repoId);
                
                if (!repoId) {
                    console.error('No repository loaded');
                    showError('No repository loaded');
                    return;
                }

                // Show loading state
                const button = generateDocsButton;
                const originalText = button.textContent;
                button.disabled = true;
                button.textContent = 'Generating Documentation...';
                addMessage('Generating documentation for all files. This may take a few minutes...', 'system');

                try {
                    console.log('Sending request to /generate-docs');
                    const response = await fetch('/generate-docs', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/zip'
                        },
                        body: JSON.stringify({ repo_id: repoId })
                    });

                    console.log('Response status:', response.status);
                    console.log('Response headers:', Object.fromEntries(response.headers.entries()));
                    
                    if (!response.ok) {
                        const errorText = await response.text();
                        console.error('Error response:', errorText);
                        let errorMessage = 'Failed to generate documentation';
                        try {
                            const errorData = JSON.parse(errorText);
                            errorMessage = errorData.error || errorMessage;
                        } catch (e) {
                            errorMessage = errorText || errorMessage;
                        }
                        throw new Error(errorMessage);
                    }

                    // Get the blob from the response
                    const blob = await response.blob();
                    console.log('Received blob:', blob);
                    console.log('Blob size:', blob.size);
                    
                    if (blob.size === 0) {
                        throw new Error('Received empty file');
                    }
                    
                    // Create a download link
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'documented_code.zip';
                    document.body.appendChild(a);
                    a.click();
                    
                    // Clean up
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    
                    addMessage('Documentation generated and downloaded successfully!', 'system');
                } catch (error) {
                    console.error('Error in documentation generation:', error);
                    showError(error.message);
                } finally {
                    // Restore button state
                    button.disabled = false;
                    button.textContent = originalText;
                }
            });
        } else {
            console.log('Generate docs button not found yet - will try again after repository upload');
        }
    }

    // Helper functions
    function showStatus(message, type) {
        const statusDiv = document.getElementById('upload-status');
        statusDiv.textContent = message;
        statusDiv.className = type;
    }

    function showError(message) {
        const chatMessages = document.getElementById('chat-messages');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message error';
        errorDiv.textContent = message;
        chatMessages.appendChild(errorDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showRepositoryInfo(data) {
        const repoInfo = document.getElementById('repository-info');
        const chatSection = document.getElementById('chat-section');
        const repoSummary = document.getElementById('repo-summary');
        
        repoSummary.textContent = data.summary;
        repoInfo.style.display = 'block';
        chatSection.style.display = 'block';
        
        // Store the repository ID in sessionStorage
        sessionStorage.setItem('repo_id', data.repo_id);
        console.log('Stored repo_id:', data.repo_id);
    }

    function addMessage(text, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = text;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addCodeReference(ref) {
        const refDiv = document.createElement('div');
        refDiv.className = 'message code-reference';
        
        // Create header with file info
        const header = document.createElement('div');
        header.className = 'code-header';
        header.textContent = `File: ${ref.file}`;
        if (ref.description) {
            header.textContent += ` - ${ref.description}`;
        }
        refDiv.appendChild(header);
        
        // Create code container
        const codeContainer = document.createElement('div');
        codeContainer.className = 'code-container';
        
        // Split code into lines and add line numbers
        const lines = ref.code.split('\n');
        const codeBlock = document.createElement('pre');
        const codeContent = document.createElement('code');
        
        // Add line numbers and code
        const formattedCode = lines.map((line, i) => {
            const lineNumber = i + 1;
            const isHighlighted = ref.highlight_lines && ref.highlight_lines.includes(lineNumber);
            const lineClass = isHighlighted ? 'highlight' : '';
            return `<span class="line-number">${lineNumber}</span><span class="line-content ${lineClass}">${line}</span>`;
        }).join('\n');
        
        codeContent.innerHTML = formattedCode;
        codeBlock.appendChild(codeContent);
        codeContainer.appendChild(codeBlock);
        refDiv.appendChild(codeContainer);
        
        chatMessages.appendChild(refDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Allow Enter key to send query
    queryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendQueryButton.click();
        }
    });

    // Function to show documentation in a modal
    function showDocumentationModal(docs) {
        // Create modal container
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Repository Documentation</h2>
                    <button class="close-button">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="docs-content">
                        ${formatDocumentation(docs)}
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="download-button">Download as Markdown</button>
                </div>
            </div>
        `;

        // Add modal to the page
        document.body.appendChild(modal);

        // Handle close button
        modal.querySelector('.close-button').addEventListener('click', () => {
            document.body.removeChild(modal);
        });

        // Handle download button
        modal.querySelector('.download-button').addEventListener('click', () => {
            downloadMarkdown(docs);
        });

        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }

    // Function to format documentation for display
    function formatDocumentation(docs) {
        let html = `
            <div class="docs-section">
                <h3>Overview</h3>
                <p>${docs.overview}</p>
            </div>
            <div class="docs-section">
                <h3>Architecture</h3>
                <p>${docs.architecture}</p>
            </div>
            <div class="docs-section">
                <h3>Components</h3>
        `;

        docs.components.forEach(component => {
            html += `
                <div class="component">
                    <h4>${component.name}</h4>
                    <p class="file-path">File: ${component.file}</p>
                    <p>${component.description}</p>
                    <h5>Methods:</h5>
                    <ul>
                        ${component.methods.map(method => `<li>${method}</li>`).join('')}
                    </ul>
                </div>
            `;
        });

        html += `
            </div>
            <div class="docs-section">
                <h3>Dependencies</h3>
        `;

        Object.entries(docs.dependencies).forEach(([file, deps]) => {
            html += `
                <div class="dependency">
                    <h4>${file}</h4>
                    <ul>
                        ${deps.map(dep => `<li>${dep}</li>`).join('')}
                    </ul>
                </div>
            `;
        });

        html += `
            </div>
            <div class="docs-section">
                <h3>Usage Guide</h3>
                <p>${docs.usage_guide}</p>
            </div>
        `;

        return html;
    }

    // Function to download documentation as markdown
    function downloadMarkdown(docs) {
        let markdown = `# Repository Documentation

## Overview
${docs.overview}

## Architecture
${docs.architecture}

## Components
`;

        docs.components.forEach(component => {
            markdown += `
### ${component.name}
**File:** ${component.file}

${component.description}

#### Methods
`;
            component.methods.forEach(method => {
                markdown += `- ${method}\n`;
            });
        });

        markdown += `
## Dependencies
`;

        Object.entries(docs.dependencies).forEach(([file, deps]) => {
            markdown += `
### ${file}
`;
            deps.forEach(dep => {
                markdown += `- ${dep}\n`;
            });
        });

        markdown += `
## Usage Guide
${docs.usage_guide}
`;

        // Create and trigger download
        const blob = new Blob([markdown], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'repository_documentation.md';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
});