// static/script.js
document.addEventListener('DOMContentLoaded', () => {
    const recipeUrlInput = document.getElementById('recipeUrl');
    const scrapeButton = document.getElementById('scrapeButton');
    const statusMessage = document.getElementById('statusMessage');
    const resultsArea = document.getElementById('resultsArea');
    const structuredDataDiv = document.getElementById('structuredData');
    const jsonDataOutput = document.getElementById('jsonDataOutput');
    const copyJsonButton = document.getElementById('copyJsonButton');
    const downloadJsonButton = document.getElementById('downloadJsonButton'); // Get the new button

    let currentRecipeData = null; // Variable to store the latest successful scrape data

    scrapeButton.addEventListener('click', async () => {
        const url = recipeUrlInput.value.trim();
        if (!url) {
            displayStatus('Please enter a valid HelloFresh recipe URL.', true);
            return;
        }

        // Basic URL validation
        try {
            new URL(url);
            if (!url.toLowerCase().includes('hellofresh.')) { // Allow various TLDs like .com, .co.uk, .ca, .de etc.
                console.warn("URL might not be a HelloFresh domain, but attempting scrape.");
            }
        } catch (_) {
            displayStatus('Invalid URL format.', true);
            return;
        }

        displayStatus('Fetching and parsing recipe data... This may take a moment.', false);
        resultsArea.style.display = 'none';
        structuredDataDiv.innerHTML = '';
        jsonDataOutput.textContent = '';
        currentRecipeData = null; // Reset current data

        try {
            const response = await fetch('/scrape-recipe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url }),
            });

            const result = await response.json();
            currentRecipeData = result; // Store the result

            if (!response.ok) {
                const errorMessage = result.error || `Server responded with status: ${response.status}`;
                displayStatus(`Error: ${errorMessage}`, true);
                jsonDataOutput.textContent = JSON.stringify(result, null, 2);
                resultsArea.style.display = 'block';
                return;
            }
            
            if (result.error) {
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
            currentRecipeData = { error: error.message, details: "Network error or server unreachable." };
            displayStatus(`Client-side error: ${error.message}. Check browser console.`, true);
            jsonDataOutput.textContent = JSON.stringify(currentRecipeData, null, 2);
            resultsArea.style.display = 'block';
        }
    });

    copyJsonButton.addEventListener('click', () => {
        if (jsonDataOutput.textContent) {
            navigator.clipboard.writeText(jsonDataOutput.textContent)
                .then(() => {
                    displayStatus('JSON copied to clipboard!', false, true);
                    setTimeout(() => displayStatus('Enter a URL and click "Scrape Recipe".'), 2000);
                })
                .catch(err => {
                    console.error('Failed to copy JSON: ', err);
                    displayStatus('Failed to copy JSON. Please copy manually.', true);
                });
        } else {
            displayStatus('No JSON data to copy.', true);
        }
    });

    // Event listener for the new Download JSON button
    downloadJsonButton.addEventListener('click', () => {
        if (!currentRecipeData || Object.keys(currentRecipeData).length === 0) {
            displayStatus('No recipe data available to download.', true);
            return;
        }
        if (currentRecipeData.error && !currentRecipeData.name) { // If it's just an error object
            displayStatus('Cannot download error data. Please scrape a valid recipe first.', true);
            return;
        }


        // Create a filename (e.g., "korean-beef-bibimbap.json")
        let filename = "recipe_data.json";
        if (currentRecipeData.name) {
            filename = currentRecipeData.name
                .toLowerCase()
                .replace(/\s+/g, '-') // Replace spaces with hyphens
                .replace(/[^\w-]+/g, '') // Remove non-alphanumeric characters except hyphens
                .substring(0, 50) + ".json"; // Limit length and add extension
            if (filename === ".json") filename = "recipe_data.json"; // fallback if name was all special chars
        }

        const jsonStr = JSON.stringify(currentRecipeData, null, 2); // Pretty print the JSON
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a); // Required for Firefox
        a.click();

        // Clean up: remove the temporary anchor and revoke the blob URL
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        displayStatus(`JSON data download initiated as ${filename}`, false, true);
        setTimeout(() => displayStatus('Enter a URL and click "Scrape Recipe".'), 3000);
    });


    function displayStatus(message, isError = false, isSuccess = false) {
        statusMessage.textContent = message;
        statusMessage.className = '';
        if (isError) {
            statusMessage.classList.add('error');
        } else if (isSuccess) {
            statusMessage.classList.add('success');
        }
    }

    function displayStructuredData(data) {
        structuredDataDiv.innerHTML = ''; 

        if (!data || Object.keys(data).length === 0) {
            structuredDataDiv.innerHTML = '<p>No data to display.</p>';
            return;
        }

        let html = `<h4>${data.name || 'Unnamed Recipe'}</h4>`;
        if (data.description) html += `<p><strong>Description:</strong> ${data.description}</p>`;
        
        html += `<p><strong>Source:</strong> <a href="${data.source_url}" target="_blank" rel="noopener noreferrer">${data.source_url}</a></p>`;
        if (data.external_id) html += `<p><strong>ID:</strong> ${data.external_id}</p>`;
        
        let timeInfoParts = [];
        if (data.prep_time_minutes) timeInfoParts.push(`<strong>Prep:</strong> ${data.prep_time_minutes} min`);
        if (data.cook_time_minutes) timeInfoParts.push(`<strong>Cook:</strong> ${data.cook_time_minutes} min`);
        if (data.total_time_minutes) timeInfoParts.push(`<strong>Total:</strong> ${data.total_time_minutes} min`);
        if (timeInfoParts.length > 0) html += `<p>${timeInfoParts.join(' | ')}</p>`;
        
        if (data.servings) html += `<p><strong>Servings:</strong> ${data.servings}</p>`;

        if (data.image_url) {
            html += `<h4>Recipe Image:</h4><img src="${data.image_url}" alt="${data.name || 'Recipe Image'}" style="max-width:100%; height:auto; border-radius:4px; margin-bottom:10px;">`;
        }

        if (data.ingredients && data.ingredients.length > 0) {
            html += `<h4>Ingredients:</h4><ul>`;
            data.ingredients.forEach(ing => {
                let ingAllergensText = "";
                if (ing.allergens_in_item && ing.allergens_in_item.length > 0) {
                    ingAllergensText = ` <small>(Contains: ${ing.allergens_in_item.join(', ')})</small>`;
                }
                html += `<li class="ingredient-item">
                    ${ing.quantity ? `<strong>${ing.quantity}</strong> ` : ''}
                    ${ing.unit ? `${ing.unit} ` : ''}
                    ${ing.name || ''}
                    <em>(Full: ${ing.full_text})${ingAllergensText}</em>
                </li>`;
            });
            html += `</ul>`;
        }
        
        if (data.allergens_extracted_from_ingredients && data.allergens_extracted_from_ingredients.length > 0) {
            html += `<h4>Overall Detected Allergens:</h4><p><small>${data.allergens_extracted_from_ingredients.join(', ')}</small></p>`;
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

        if (data.cuisine) html += `<p><strong>Cuisine:</strong> ${data.cuisine}</p>`;
        if (data.category) html += `<p><strong>Category:</strong> ${data.category}</p>`;
        if (data.date_published) html += `<p><small>Published: ${new Date(data.date_published).toLocaleDateString()}</small></p>`;
        
        html += `<p><small>Scraped at: ${new Date(data.scraped_at_timestamp).toLocaleString()}</small></p>`;
        if(data.disclaimer) html += `<p><small><em>${data.disclaimer}</em></small></p>`;

        structuredDataDiv.innerHTML = html;
    }
});