// static/script.js
document.addEventListener('DOMContentLoaded', () => {
    const recipeUrlInput = document.getElementById('recipeUrl');
    const scrapeButton = document.getElementById('scrapeButton');
    const statusMessage = document.getElementById('statusMessage');
    const resultsArea = document.getElementById('resultsArea');
    const structuredDataDiv = document.getElementById('structuredData');
    const jsonDataOutput = document.getElementById('jsonDataOutput');
    const copyJsonButton = document.getElementById('copyJsonButton');

    scrapeButton.addEventListener('click', async () => {
        const url = recipeUrlInput.value.trim();
        if (!url) {
            displayStatus('Please enter a valid HelloFresh recipe URL.', true);
            return;
        }

        // Basic URL validation (optional, as backend also validates)
        try {
            new URL(url); // Checks if URL is structurally valid
            if (!url.toLowerCase().includes('hellofresh.com')) {
                // Soft warning, still proceed
                console.warn("URL might not be a HelloFresh domain, but attempting scrape.");
            }
        } catch (_) {
            displayStatus('Invalid URL format.', true);
            return;
        }


        displayStatus('Fetching and parsing recipe data... This may take a moment.', false);
        resultsArea.style.display = 'none'; // Hide previous results
        structuredDataDiv.innerHTML = ''; // Clear previous structured data
        jsonDataOutput.textContent = ''; // Clear previous JSON data

        try {
            const response = await fetch('/scrape-recipe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url }),
            });

            const result = await response.json();

            if (!response.ok) {
                // Handle HTTP errors from our API (e.g., 400, 500)
                const errorMessage = result.error || `Server responded with status: ${response.status}`;
                displayStatus(`Error: ${errorMessage}`, true);
                jsonDataOutput.textContent = JSON.stringify(result, null, 2); // Show error JSON
                resultsArea.style.display = 'block'; // Show area to display error JSON
                return;
            }
            
            if (result.error) {
                // Handle errors reported within a 200 OK response's JSON payload (if any)
                displayStatus(`Scraping Error: ${result.error}`, true);
                jsonDataOutput.textContent = JSON.stringify(result, null, 2);
            } else {
                displayStatus('Recipe data scraped successfully!', false, true);
                displayStructuredData(result);
                jsonDataOutput.textContent = JSON.stringify(result, null, 2);
            }
            resultsArea.style.display = 'block';

        } catch (error) {
            console.error('Fetch API Error:', error);
            displayStatus(`Client-side error: ${error.message}. Check browser console.`, true);
            jsonDataOutput.textContent = JSON.stringify({ error: error.message, details: "Network error or server unreachable." }, null, 2);
            resultsArea.style.display = 'block';
        }
    });

    copyJsonButton.addEventListener('click', () => {
        if (jsonDataOutput.textContent) {
            navigator.clipboard.writeText(jsonDataOutput.textContent)
                .then(() => {
                    displayStatus('JSON copied to clipboard!', false, true); // Temporary success message
                    setTimeout(() => displayStatus('Enter a URL and click "Scrape Recipe".'), 2000); // Reset status
                })
                .catch(err => {
                    console.error('Failed to copy JSON: ', err);
                    displayStatus('Failed to copy JSON. Please copy manually.', true);
                });
        }
    });

    function displayStatus(message, isError = false, isSuccess = false) {
        statusMessage.textContent = message;
        statusMessage.className = ''; // Reset classes
        if (isError) {
            statusMessage.classList.add('error');
        } else if (isSuccess) {
            statusMessage.classList.add('success');
        }
    }

    function displayStructuredData(data) {
        structuredDataDiv.innerHTML = ''; // Clear previous

        if (!data || Object.keys(data).length === 0) {
            structuredDataDiv.innerHTML = '<p>No data to display.</p>';
            return;
        }

        // Create a more readable display
        let html = `<h4>${data.name || 'Unnamed Recipe'}</h4>`;
        if (data.description) html += `<p><strong>Description:</strong> ${data.description}</p>`;
        
        html += `<p><strong>Source:</strong> <a href="${data.source_url}" target="_blank">${data.source_url}</a></p>`;
        if (data.external_id) html += `<p><strong>ID:</strong> ${data.external_id}</p>`;
        
        html += `<p>
            ${data.prep_time_minutes ? `<strong>Prep:</strong> ${data.prep_time_minutes} min | ` : ''}
            ${data.cook_time_minutes ? `<strong>Cook:</strong> ${data.cook_time_minutes} min | ` : ''}
            ${data.total_time_minutes ? `<strong>Total:</strong> ${data.total_time_minutes} min` : ''}
        </p>`;
        
        if (data.servings) html += `<p><strong>Servings:</strong> ${data.servings}</p>`;

        if (data.image_url) {
            html += `<h4>Recipe Image:</h4><img src="${data.image_url}" alt="${data.name || 'Recipe Image'}" style="max-width:100%; height:auto; border-radius:4px; margin-bottom:10px;">`;
        }

        if (data.ingredients && data.ingredients.length > 0) {
            html += `<h4>Ingredients:</h4><ul>`;
            data.ingredients.forEach(ing => {
                html += `<li class="ingredient-item">
                    ${ing.quantity ? `<strong>${ing.quantity}</strong> ` : ''}
                    ${ing.unit ? `${ing.unit} ` : ''}
                    ${ing.name || ''}
                    <em>(Full: ${ing.full_text})</em>
                </li>`;
            });
            html += `</ul>`;
        }

        if (data.steps && data.steps.length > 0) {
            html += `<h4>Steps:</h4><ol>`;
            data.steps.forEach(step => {
                html += `<li>${step}</li>`;
            });
            html += `</ol>`;
        }

        if (data.nutrition_info && Object.keys(data.nutrition_info).length > 0) {
            html += `<h4>Nutrition Info (per serving):</h4><ul>`;
            for (const [key, value] of Object.entries(data.nutrition_info)) {
                html += `<li class="nutrition-item"><strong>${key.charAt(0).toUpperCase() + key.slice(1)}:</strong> ${value}</li>`;
            }
            html += `</ul>`;
        }

        if (data.tags_array && data.tags_array.length > 0) {
            html += `<h4>Tags:</h4><p>${data.tags_array.join(', ')}</p>`;
        }
        
        html += `<p><small>Scraped at: ${new Date(data.scraped_at_timestamp).toLocaleString()}</small></p>`;
        if(data.disclaimer) html += `<p><small><em>${data.disclaimer}</em></small></p>`;


        structuredDataDiv.innerHTML = html;
    }
});