from flask import Flask, request, jsonify
from PIL import Image
from flask_cors import CORS
import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification, GPT2LMHeadModel, GPT2Tokenizer
import requests

app = Flask(__name__)
CORS(app)

# Load image classification model and processor
processor = AutoImageProcessor.from_pretrained("illusion002/food-image-classification")
model = AutoModelForImageClassification.from_pretrained("illusion002/food-image-classification")

# Load GPT-2 model and tokenizer for recipe generation
recipe_model = GPT2LMHeadModel.from_pretrained('gpt2')  # Use your fine-tuned recipe model path if available
recipe_tokenizer = GPT2Tokenizer.from_pretrained('gpt2')  # Use your fine-tuned tokenizer path if available

# Check if the model has a 'label' mapping
label_map = model.config.id2label if hasattr(model.config, 'id2label') else None


@app.route('/classify', methods=['POST'])
def classify_image():
    # Check if the request contains an image file
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    image_file = request.files['image']
    try:
        # Open and preprocess the image
        image = Image.open(image_file).convert('RGB').resize((224, 224))  # Ensure it's in RGB mode
        # Use the processor to prepare the image for the model
        inputs = processor(images=image, return_tensors="pt")

        # Perform prediction (forward pass)
        with torch.no_grad():
            outputs = model(**inputs)

        # Get predicted class label index
        predicted_index = torch.argmax(outputs.logits, dim=-1).item()

        # Check if id2label exists and get the predicted label
        if label_map:
            predicted_label = label_map.get(predicted_index, "Unknown")
        else:
            predicted_label = str(predicted_index)  # If no label map, just return the index

        return jsonify({'dishName': predicted_label})  # Use dishName instead of predicted_label

    except Exception as e:
        print(f"Error processing the image: {e}")  # Log error details to the server console
        return jsonify({'error': f'Failed to process image: {str(e)}'}), 500


@app.route('/generate_recipe', methods=['POST'])
def generate_recipe():
    data = request.get_json()
    dish_name = data.get('dishName', '')

    if not dish_name:
        return jsonify({'error': 'No dish name provided'}), 400

    try:
       
        input_text = f"Generate a full step wise recipe for {dish_name}:"
        inputs = recipe_tokenizer.encode(input_text, return_tensors="pt")  

        
        outputs = recipe_model.generate(
            inputs,
            max_length=150,
            num_return_sequences=1,
            temperature=0.7,
            top_p=0.9,      
            repetition_penalty=2.0  
        )

      
        recipe = recipe_tokenizer.decode(outputs[0], skip_special_tokens=True)

        
        recipe = recipe.replace(input_text, '').strip()

        return jsonify({'recipe': recipe})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# # Fatsecret API integration for fetching recipes based on dish name
# FATSECRET_API_URL = "https://platform.fatsecret.com/rest/recipes/search/v3"
# FATSECRET_API_KEY = "YOUR_FATSECRET_API_KEY"  # Replace with your actual API key

# def fetch_fatsecret_data(search_query):
#     """Fetch recipe data from Fatsecret API."""
#     params = {
#         'method': 'recipes.search.v3',
#         'search_expression': search_query,
#         'max_results': 5,
#         'page_number': 0,
#         'format': 'json',
#     }
#     headers = {
#         'Authorization': f'Bearer {FATSECRET_API_KEY}'  # Replace with OAuth token if needed
#     }
    
#     response = requests.get(FATSECRET_API_URL, params=params, headers=headers)
    
#     if response.status_code == 200:
#         return response.json()
#     else:
#         print(f"Error fetching data from Fatsecret API: {response.status_code}")
#         return None

# @app.route('/getrecipe', methods=['GET'])
# def get_recipe():
#     data = request.get_json()  # Get the incoming JSON data
#     dish_name = data.get('dishName', '')

#     if not dish_name:
#         return jsonify({'error': 'No dish name provided'}), 400

#     # Fetch recipe data from Fatsecret API based on the dish name
#     fatsecret_data = fetch_fatsecret_data(dish_name)

#     if fatsecret_data and 'recipes' in fatsecret_data:
#         recipes = fatsecret_data['recipes']['recipe']
#         recipe_details = []
#         for recipe in recipes:
#             recipe_details.append({
#                 'name': recipe['recipe_name'],
#                 'description': recipe.get('recipe_description', 'No description available'),
#                 'calories': recipe['recipe_nutrition'].get('calories', 'N/A')
#             })
#     else:
#         recipe_details = [{'name': 'No recipes found', 'description': '', 'calories': ''}]

#     return jsonify({
#         'dishName': dish_name,
#         'recipes': recipe_details
#     })


# if __name__ == '__main__':
#     app.run(debug=True)
